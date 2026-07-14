import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { ConversationPanel } from '@/components/chat/ConversationPanel';
import { ToolSidePanel } from '@/components/chat/ToolSidePanel';
import { ScoringPanel } from '@/components/chat/ScoringPanel';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { SessionEditSheet } from '@/components/sessions/SessionEditSheet';
import { SessionInfoCard } from '@/components/sessions/SessionInfoCard';
import { DeleteConfirmDialog } from '@/components/ui/delete-confirm-dialog';
import { api } from '@/services/api';
import { useSessionHistoryStore } from '@/stores/sessionHistoryStore';
import { ArrowLeft, Loader2, Pencil, Trash2 } from 'lucide-react';
import { extractSessionMetadata, extractJudgeMetadata } from '@/lib/metadataUtils';
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
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isScoring, setIsScoring] = useState(false);
  const [showScoreConfig, setShowScoreConfig] = useState(false);
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const deleteSession = useSessionHistoryStore((s) => s.deleteSession);

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

  const handleDelete = async () => {
    if (!sessionId) return;
    try {
      await deleteSession(sessionId);
      toast.success('Session deleted');
      navigate('/sessions');
    } catch {
      // error set in store
    }
  };

  const handleEditSaved = () => {
    setEditOpen(false);
    // Refresh session data
    if (sessionId) {
      void api.getSession(sessionId).then(setSession);
    }
  };

  const agentMeta = useMemo(
    () => extractSessionMetadata(session?.agent_config),
    [session?.agent_config],
  );
  const judgeMeta = useMemo(
    () => extractJudgeMetadata(session?.judge_config_snapshot),
    [session?.judge_config_snapshot],
  );
  const configMetadata = useMemo(() => ({ ...agentMeta, ...judgeMeta }), [agentMeta, judgeMeta]);

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
    <div className="space-y-4">
      {/* Header: breadcrumb + title + action buttons */}
      <div>
        <Link
          to="/sessions"
          className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] text-text-2 hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All sessions
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <h1 className="text-[25px] font-semibold tracking-[-0.02em]">
              {session.name ?? `Session ${session.id.slice(0, 8)}`}
            </h1>
            {isSessionScoring && (
              <span className="inline-flex items-center rounded-full bg-warn-bg px-2.5 py-0.5 text-[10.5px] font-medium text-warn">
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Scoring...
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
              onClick={() => setEditOpen(true)}
              aria-label="Edit session"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button
              className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
              onClick={() => setDeleteOpen(true)}
              aria-label="Delete session"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
            {isEnded && !hasScores && !showScoreConfig && !isSessionScoring && (
              <button
                className="rounded-[9px] bg-primary px-3 py-1.5 text-[12px] font-medium text-primary-foreground transition-opacity hover:opacity-90"
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
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Optional: Judge config panel */}
      {showScoreConfig && (
        <div className="rounded-[14px] border border-border bg-card p-5 shadow-sm space-y-4">
          <h3 className="text-[10.5px] font-semibold tracking-[0.06em] uppercase text-text-3">
            Select Judge for Scoring
          </h3>
          <JudgeConfigPanel value={judgeConfig} onChange={setJudgeConfig} />
          <div className="flex gap-2">
            <button
              className="rounded-[9px] bg-primary px-3 py-1.5 text-[12px] font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
              onClick={() => void handleScore()}
              disabled={!judgeConfig || isScoring}
            >
              {isScoring ? 'Scoring...' : 'Run Judge'}
            </button>
            <button
              className="rounded-[9px] border border-border px-3 py-1.5 text-[12px] font-medium text-text-2 transition-colors hover:bg-surface-3"
              onClick={() => setShowScoreConfig(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Row 1: Scores + Session Details */}
      <div className="flex flex-col gap-4 lg:flex-row">
        <div className="lg:w-[50%] min-w-0">
          <ScoringPanel scores={scores} isSessionEnded={isEnded} />
        </div>
        <div className="lg:w-[50%] min-w-0">
          <SessionInfoCard
            session={session}
            messageCount={messages.length}
            metadata={configMetadata}
          />
        </div>
      </div>

      {/* Row 2: Conversation + Tool Inspector */}
      <div className="flex flex-col gap-4 lg:flex-row lg:h-[calc(100vh-480px)] lg:min-h-[400px]">
        <div className="min-w-0 min-h-0 h-[500px] lg:h-auto lg:flex-1">
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
      </div>

      {/* Edit Sheet */}
      {editOpen && session && (
        <SessionEditSheet
          open={editOpen}
          onOpenChange={(open) => {
            if (!open) handleEditSaved();
          }}
          session={session}
        />
      )}

      {/* Delete Confirmation */}
      <DeleteConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete session"
        description="Are you sure you want to delete session"
        entityName={session.name ?? session.id.slice(0, 8)}
        onConfirm={handleDelete}
        cascadeInfo="All results linked to this session will also be deleted."
      />
    </div>
  );
}
