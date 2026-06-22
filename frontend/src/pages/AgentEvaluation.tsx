import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { HarnessSelector } from '@/components/evaluation/HarnessSelector';
import { ProviderSelector } from '@/components/evaluation/ProviderSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { ConversationPanel } from '@/components/chat/ConversationPanel';
import { ToolSidePanel } from '@/components/chat/ToolSidePanel';
import { ToolInspector } from '@/components/chat/ToolInspector';
import { ScoringPanel } from '@/components/chat/ScoringPanel';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useSessionStore } from '@/stores/sessionStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { api } from '@/services/api';
import {
  Play,
  Square,
  RefreshCw,
  Wifi,
  WifiOff,
  Clock,
  ExternalLink,
  Wrench,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Loader2,
  SkipForward,
  BarChart3,
} from 'lucide-react';
import type { ModelEndpoint, JudgeReference, ToolServer } from '@/types';

type PagePhase = 'configure' | 'active' | 'scoring' | 'review';

function SessionErrorBanner({ error }: { error: string }) {
  const [expanded, setExpanded] = useState(false);
  const firstLine = error.split('\n')[0];
  const hasMultipleLines = error.includes('\n');

  return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-destructive">{firstLine}</p>
          {hasMultipleLines && (
            <>
              <button
                type="button"
                className="mt-1 flex items-center gap-1 text-xs font-medium text-destructive/70 hover:text-destructive"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {expanded ? 'Hide details' : 'Show details'}
              </button>
              {expanded && (
                <pre className="mt-2 max-h-60 overflow-auto rounded bg-zinc-950 p-3 text-xs text-zinc-300 whitespace-pre-wrap">
                  {error}
                </pre>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AgentEvaluation() {
  const [phase, setPhase] = useState<PagePhase>('configure');
  const [modelEndpoint, setModelEndpoint] = useState<ModelEndpoint>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [systemPrompt, setSystemPrompt] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [toolServers, setToolServers] = useState<ToolServer[]>([]);
  const [selectedToolServerIds, setSelectedToolServerIds] = useState<string[]>([]);
  const [selectedHarnessId, setSelectedHarnessId] = useState<string | undefined>();
  const [selectedHarnessType, setSelectedHarnessType] = useState<string>('builtin');

  const { isLoading: evalLoading, setLoading: setEvalLoading } = useEvaluationStore();
  const { selectedEvaluatorId } = useEvaluatorStore();

  const {
    currentSession,
    messages,
    toolCalls,
    scores,
    isConnected,
    isProcessing,
    isScoring,
    error,
    createSession,
    sendMessage,
    endSession,
    scoreSession,
    connectWebSocket,
    disconnectWebSocket,
    resetSession,
  } = useSessionStore();

  const isSubprocessHarness = selectedHarnessType === 'subprocess';
  const isConfigValid = Boolean(
    (isSubprocessHarness || modelEndpoint) && judgeConfig && selectedEvaluatorId,
  );

  // Load available tool servers
  useEffect(() => {
    api
      .listToolServers({ enabled: true })
      .then(setToolServers)
      .catch(() => {
        /* ignore — tool servers are optional */
      });
  }, []);

  // Session timer
  useEffect(() => {
    if (phase !== 'active') return;

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [phase]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      disconnectWebSocket();
    };
  }, [disconnectWebSocket]);

  // Watch for session status changes via store subscription
  useEffect(() => {
    const unsubscribe = useSessionStore.subscribe((state, prevState) => {
      const status = state.currentSession?.status;
      const prevStatus = prevState.currentSession?.status;
      if (status === prevStatus) return;

      if (status === 'completed') {
        setPhase('review');
        toast.success('Session completed');
        useNotificationStore.getState().addNotification({
          type: 'success',
          title: 'Session Completed',
          message: 'Agent evaluation session has ended.',
        });
      }
    });
    return unsubscribe;
  }, []);

  const handleHarnessChange = useCallback((harnessId: string, harnessType: string) => {
    setSelectedHarnessId(harnessId);
    setSelectedHarnessType(harnessType);
  }, []);

  const handleStart = useCallback(async () => {
    if (!judgeConfig) return;
    if (!isSubprocessHarness && !modelEndpoint) return;

    try {
      setEvalLoading(true);

      const sessionName = isSubprocessHarness
        ? `Agent Chat - ${selectedHarnessId}`
        : `Agent Chat - ${modelEndpoint?.name}`;

      await createSession({
        name: sessionName,
        mode: 'live',
        agent_config: {
          ...(modelEndpoint && {
            provider_id: modelEndpoint.provider_id,
            default_model: modelEndpoint.default_model,
            api_base: modelEndpoint.api_base,
          }),
          ...(systemPrompt.trim() && { system_prompt: systemPrompt.trim() }),
          ...(selectedEvaluatorId && { evaluator_id: selectedEvaluatorId }),
          ...(selectedToolServerIds.length > 0 && {
            tool_server_ids: selectedToolServerIds,
          }),
          ...(selectedHarnessId &&
            selectedHarnessId !== 'builtin-litellm' && {
              harness_id: selectedHarnessId,
            }),
        },
        judge_config: {
          provider_id: judgeConfig.provider_id,
        },
      });

      const session = useSessionStore.getState().currentSession;
      if (session) {
        connectWebSocket(session.id);
        setElapsedSeconds(0);
        setPhase('active');
        toast.success('Session started');
      }
    } catch (err) {
      toast.error('Failed to start session');
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Failed to Start Session',
        message: err instanceof Error ? err.message : 'An unknown error occurred',
        details: err instanceof Error ? err.stack : undefined,
      });
    } finally {
      setEvalLoading(false);
    }
  }, [
    modelEndpoint,
    judgeConfig,
    systemPrompt,
    selectedEvaluatorId,
    selectedToolServerIds,
    selectedHarnessId,
    isSubprocessHarness,
    setEvalLoading,
    createSession,
    connectWebSocket,
  ]);

  const handleEndSession = useCallback(async () => {
    try {
      await endSession();
      setPhase('scoring');
      toast.success('Session ended');
    } catch {
      toast.error('Failed to end session');
    }
  }, [endSession]);

  const handleScoreSession = useCallback(async () => {
    if (!judgeConfig?.provider_id) return;
    try {
      await scoreSession({ provider_id: judgeConfig.provider_id });
      setPhase('review');
      toast.success('Session scored successfully');
    } catch {
      toast.error('Failed to score session');
    }
  }, [judgeConfig, scoreSession]);

  const handleSkipScoring = useCallback(() => {
    setPhase('review');
  }, []);

  const handleReconnect = useCallback(() => {
    if (currentSession) {
      connectWebSocket(currentSession.id);
    }
  }, [currentSession, connectWebSocket]);

  const handleNewSession = useCallback(() => {
    resetSession();
    setPhase('configure');
    setModelEndpoint(undefined);
    setJudgeConfig(undefined);
    setSystemPrompt('');
    setElapsedSeconds(0);
    setSelectedToolServerIds([]);
    setSelectedHarnessId(undefined);
    setSelectedHarnessType('builtin');
    useEvaluatorStore.getState().resetSelection();
  }, [resetSession]);

  const formatElapsed = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex h-full flex-col space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agent/Chat Evaluation</h1>
        <p className="text-muted-foreground">
          Multi-turn conversational evaluation with tool call tracing, live or simulated sessions.
        </p>
      </div>
      <Separator />

      {/* Configure Phase */}
      {phase === 'configure' && (
        <>
          <EvaluatorSelector mode="agent" />
          <HarnessSelector value={selectedHarnessId} onChange={handleHarnessChange} />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              {!isSubprocessHarness && (
                <ProviderSelector value={modelEndpoint} onChange={setModelEndpoint} />
              )}
              <div className="space-y-2">
                <Label htmlFor="system-prompt">System Prompt (optional)</Label>
                <Textarea
                  id="system-prompt"
                  placeholder="Provide an optional system prompt for the agent..."
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  rows={4}
                />
              </div>
              {toolServers.length > 0 && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-1.5">
                    <Wrench className="h-3.5 w-3.5" />
                    Tool Servers (optional)
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Select MCP tool servers the agent can use during the session.
                  </p>
                  <div className="space-y-2 rounded-md border p-3">
                    {toolServers.map((server) => (
                      <label
                        key={server.id}
                        className="flex items-center gap-2 text-sm cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-input"
                          checked={selectedToolServerIds.includes(server.id)}
                          onChange={(e) => {
                            setSelectedToolServerIds((prev) =>
                              e.target.checked
                                ? [...prev, server.id]
                                : prev.filter((id) => id !== server.id),
                            );
                          }}
                        />
                        <span className="font-medium">{server.name}</span>
                        {server.type === 'mcp_stdio' && (
                          <Badge variant="outline" className="text-[10px]">
                            MCP
                          </Badge>
                        )}
                        {server.type === 'standalone' && (
                          <Badge variant="outline" className="text-[10px]">
                            Standalone
                          </Badge>
                        )}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div>
              <JudgeConfigPanel value={judgeConfig} onChange={setJudgeConfig} />
            </div>
          </div>
          <Button
            className="w-full"
            disabled={!isConfigValid || evalLoading}
            onClick={() => void handleStart()}
          >
            <Play className="mr-2 h-4 w-4" />
            {evalLoading ? 'Starting...' : 'Start Session'}
          </Button>
        </>
      )}

      {/* Active Phase */}
      {phase === 'active' && (
        <>
          {/* Header bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Badge variant={isConnected ? 'default' : 'destructive'} className="gap-1">
                {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                {isConnected ? 'Connected' : 'Disconnected'}
              </Badge>
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                {formatElapsed(elapsedSeconds)}
              </div>
            </div>
            <Button variant="destructive" size="sm" onClick={() => void handleEndSession()}>
              <Square className="mr-1.5 h-3.5 w-3.5" />
              End Session
            </Button>
          </div>

          {/* Error banners */}
          {error && !isConnected && currentSession?.status === 'active' && (
            <div className="flex items-center justify-between rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2">
              <p className="text-sm text-destructive">{error}</p>
              <Button variant="outline" size="sm" onClick={handleReconnect}>
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                Reconnect
              </Button>
            </div>
          )}
          {error && isConnected && <SessionErrorBanner error={error} />}

          {/* Chat-primary layout with collapsible tool panel */}
          <div className="flex flex-1 gap-4" style={{ minHeight: '500px' }}>
            <div className="flex-1 min-w-0">
              <ConversationPanel
                messages={messages}
                isProcessing={isProcessing}
                onSend={sendMessage}
                disabled={!isConnected}
              />
            </div>
            <ToolSidePanel toolCalls={toolCalls} />
          </div>
        </>
      )}

      {/* Scoring Phase */}
      {phase === 'scoring' && (
        <>
          <div className="flex items-center gap-3">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Session Ended — Score Your Evaluation</h2>
          </div>

          <div className="flex flex-1 gap-4" style={{ minHeight: '400px' }}>
            <div className="flex-1 min-w-0">
              <ConversationPanel
                messages={messages}
                isProcessing={false}
                onSend={() => {}}
                disabled={true}
              />
            </div>
            <div className="w-[400px] shrink-0 flex flex-col gap-4">
              <JudgeConfigPanel
                value={judgeConfig}
                onChange={setJudgeConfig}
                disabled={isScoring}
              />
              <div className="flex flex-col gap-2">
                <Button
                  className="w-full"
                  onClick={() => void handleScoreSession()}
                  disabled={!judgeConfig || isScoring}
                >
                  {isScoring ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Scoring...
                    </>
                  ) : (
                    <>
                      <BarChart3 className="mr-2 h-4 w-4" />
                      Score Session
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleSkipScoring}
                  disabled={isScoring}
                >
                  <SkipForward className="mr-2 h-4 w-4" />
                  Skip Scoring
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Review Phase */}
      {phase === 'review' && (
        <>
          <div className="flex flex-1 gap-4" style={{ minHeight: '400px' }}>
            <div className="flex-1 min-w-0">
              <ConversationPanel
                messages={messages}
                isProcessing={false}
                onSend={() => {}}
                disabled={true}
              />
            </div>
            <div className="w-[400px] shrink-0 flex flex-col gap-4">
              <ToolInspector toolCalls={toolCalls} />
              <ScoringPanel scores={scores} isSessionEnded={true} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={handleNewSession}>
              <RefreshCw className="mr-2 h-4 w-4" />
              New Session
            </Button>
            {currentSession && (
              <Button variant="ghost" asChild>
                <a href={`/results/${currentSession.evaluation_id}`}>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  View in Results
                </a>
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
