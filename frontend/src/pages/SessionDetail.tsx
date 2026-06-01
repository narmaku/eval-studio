import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ConversationPanel } from '@/components/chat/ConversationPanel';
import { ToolInspector } from '@/components/chat/ToolInspector';
import { ScoringPanel } from '@/components/chat/ScoringPanel';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { api } from '@/services/api';
import type { Session, Message, ToolCall, SessionScore, JudgeReference } from '@/types';

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isScoring, setIsScoring] = useState(false);
  const [showScoreConfig, setShowScoreConfig] = useState(false);
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();

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

  const messages: Message[] = ((session?.transcript as Record<string, unknown>[] | undefined) ?? [])
    .filter((m) => m.role === 'user' || m.role === 'assistant' || m.role === 'system')
    .map((m, i) => ({
      id: String(i),
      sender: m.role === 'assistant' ? 'agent' : (m.role as 'user' | 'system'),
      content: (m.content as string) ?? '',
      timestamp: (m.timestamp as string) ?? '',
    }));

  const toolCalls: ToolCall[] = (
    (session?.transcript as Record<string, unknown>[] | undefined) ?? []
  ).flatMap((m) =>
    ((m.tool_calls as Record<string, unknown>[]) ?? []).map((tc, i) => ({
      id: (tc.id as string) ?? String(i),
      tool_name: (tc.tool_name as string) ?? '',
      arguments: (tc.arguments as Record<string, unknown>) ?? {},
      result: tc.result ?? null,
      duration_ms: (tc.duration_ms as number) ?? 0,
      timestamp: (tc.timestamp as string) ?? '',
    })),
  );

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
        {isEnded && !hasScores && !showScoreConfig && (
          <Button onClick={() => setShowScoreConfig(true)}>Score with Judge</Button>
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

      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-1 h-[600px]">
          <ConversationPanel
            messages={messages}
            isProcessing={false}
            onSend={() => {}}
            disabled={true}
          />
        </div>
        <div className="md:col-span-1 h-[600px] overflow-y-auto">
          <ToolInspector toolCalls={toolCalls} />
        </div>
        <div className="md:col-span-1 h-[600px] overflow-y-auto">
          <ScoringPanel scores={scores} isSessionEnded={isEnded} />
        </div>
      </div>
    </div>
  );
}
