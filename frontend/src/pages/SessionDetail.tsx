import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ConversationPanel } from '@/components/chat/ConversationPanel';
import { ToolSidePanel } from '@/components/chat/ToolSidePanel';
import { ScoringPanel } from '@/components/chat/ScoringPanel';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { api } from '@/services/api';
import { Loader2 } from 'lucide-react';
import type { Session, Message, ToolCall, SessionScore, JudgeReference } from '@/types';

function extractFromTranscript(transcript: Record<string, unknown>[]): {
  messages: Message[];
  toolCalls: ToolCall[];
} {
  const toolResults = new Map<string, { result: string; duration_ms: number; is_error: boolean }>();
  for (const entry of transcript) {
    if (entry.role === 'tool' && typeof entry.tool_call_id === 'string') {
      toolResults.set(entry.tool_call_id, {
        result: (entry.content as string) ?? '',
        duration_ms: (entry.duration_ms as number) ?? 0,
        is_error: (entry.is_error as boolean) ?? false,
      });
    }
  }

  const messages: Message[] = [];
  const toolCalls: ToolCall[] = [];

  for (const entry of transcript) {
    const role = entry.role as string;
    if (role !== 'user' && role !== 'assistant' && role !== 'system') continue;

    const messageId = String(messages.length);
    messages.push({
      id: messageId,
      sender: role === 'assistant' ? 'agent' : (role as 'user' | 'system'),
      content: (entry.content as string) ?? '',
      timestamp: (entry.timestamp as string) ?? '',
    });

    const entryToolCalls = entry.tool_calls as Record<string, unknown>[] | undefined;
    if (entryToolCalls) {
      for (const [i, tc] of entryToolCalls.entries()) {
        const tcId = (tc.id as string) ?? `${messageId}-${i}`;
        const result = toolResults.get(tcId);
        toolCalls.push({
          id: tcId,
          tool_name: (tc.tool_name as string) ?? '',
          arguments: (tc.arguments as Record<string, unknown>) ?? {},
          result: result?.result ?? tc.result ?? null,
          duration_ms: result?.duration_ms ?? (tc.duration_ms as number) ?? 0,
          timestamp: (tc.timestamp as string) ?? '',
          message_id: messageId,
          status: result ? (result.is_error ? 'error' : 'completed') : 'completed',
        });
      }
    }
  }

  return { messages, toolCalls };
}

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isScoring, setIsScoring] = useState(false);
  const [showScoreConfig, setShowScoreConfig] = useState(false);
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);

  const handleToolSelect = useCallback((tc: ToolCall) => setSelectedToolId(tc.id), []);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    const fetchSession = async () => {
      try {
        const s = await api.getSession(sessionId);
        if (!cancelled) {
          setSession(s);
          setIsLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load session');
          setIsLoading(false);
        }
      }
    };
    void fetchSession();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const transcript = (session?.transcript as Record<string, unknown>[] | undefined) ?? [];
  const { messages, toolCalls } = extractFromTranscript(transcript);

  const scores: SessionScore[] = session?.scores
    ? [
        {
          turn_number: null,
          dimensions: session.scores.breakdown ?? {},
          overall: session.scores.overall ?? 0,
          judge_reasoning: session.scores.reasoning ?? '',
        },
      ]
    : [];

  const handleScore = async () => {
    if (!sessionId || !judgeConfig) return;
    setIsScoring(true);
    try {
      const updated = await api.scoreSession(sessionId, {
        provider_id: judgeConfig.provider_id,
        model: judgeConfig.model,
      });
      setSession(updated);
      setShowScoreConfig(false);
      toast.success('Session scored successfully');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to score session');
    } finally {
      setIsScoring(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading session...</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-destructive font-medium">Error loading session</p>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    );
  }

  const isEnded = session.status !== 'active';
  const hasScores = scores.length > 0;
  const isSessionScoring = session.status === 'scoring';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {session.name ?? `Session ${session.id.slice(0, 8)}`}
          </h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="outline">{session.mode}</Badge>
            <Badge variant={session.status === 'completed' ? 'default' : 'secondary'}>
              {session.status}
            </Badge>
            <span className="text-muted-foreground text-sm">{messages.length} messages</span>
          </div>
        </div>
        {isSessionScoring && (
          <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            Scoring...
          </Badge>
        )}
        {isEnded && !hasScores && !showScoreConfig && !isSessionScoring && (
          <Button
            onClick={() => {
              if (session.judge_config_snapshot) {
                const snapshot = session.judge_config_snapshot;
                if (typeof snapshot.provider_id === 'string') {
                  setJudgeConfig({ provider_id: snapshot.provider_id });
                }
              }
              setShowScoreConfig(true);
            }}
          >
            Score with Judge
          </Button>
        )}
      </div>
      <Separator />

      {showScoreConfig && (
        <div className="rounded-lg border p-4 space-y-4">
          <h3 className="text-sm font-medium">Select Judge for Scoring</h3>
          <JudgeConfigPanel value={judgeConfig} onChange={setJudgeConfig} />
          <div className="flex gap-2">
            <Button onClick={() => void handleScore()} disabled={!judgeConfig || isScoring}>
              {isScoring ? 'Scoring...' : 'Run Judge'}
            </Button>
            <Button variant="outline" onClick={() => setShowScoreConfig(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      <div className="flex gap-4" style={{ height: '600px' }}>
        <div className="flex-1 min-w-0 min-h-0">
          <ConversationPanel
            messages={messages}
            isProcessing={false}
            onSend={() => {}}
            disabled={true}
            toolCalls={toolCalls}
            onToolSelect={handleToolSelect}
            selectedToolId={selectedToolId ?? undefined}
          />
        </div>
        <ToolSidePanel
          toolCalls={toolCalls}
          selectedToolId={selectedToolId}
          onToolSelect={handleToolSelect}
        />
        <div className="w-[300px] shrink-0 overflow-y-auto">
          <ScoringPanel scores={scores} isSessionEnded={isEnded} />
        </div>
      </div>
    </div>
  );
}
