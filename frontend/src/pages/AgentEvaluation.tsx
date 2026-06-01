import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { ProviderSelector } from '@/components/evaluation/ProviderSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { ConversationPanel } from '@/components/chat/ConversationPanel';
import { ToolInspector } from '@/components/chat/ToolInspector';
import { ScoringPanel } from '@/components/chat/ScoringPanel';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useSessionStore } from '@/stores/sessionStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { Play, Square, RefreshCw, Wifi, WifiOff, Clock, ExternalLink } from 'lucide-react';
import type { ModelEndpoint, JudgeReference } from '@/types';

type PagePhase = 'configure' | 'active' | 'ended';

export default function AgentEvaluation() {
  const [phase, setPhase] = useState<PagePhase>('configure');
  const [modelEndpoint, setModelEndpoint] = useState<ModelEndpoint>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [systemPrompt, setSystemPrompt] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const { isLoading: evalLoading, setLoading: setEvalLoading } = useEvaluationStore();
  const { selectedEvaluatorId } = useEvaluatorStore();

  const {
    currentSession,
    messages,
    toolCalls,
    scores,
    isConnected,
    isProcessing,
    error,
    createSession,
    sendMessage,
    endSession,
    connectWebSocket,
    disconnectWebSocket,
    resetSession,
  } = useSessionStore();

  const isConfigValid = Boolean(modelEndpoint && judgeConfig && selectedEvaluatorId);

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

      if (status === 'completed' || status === 'failed') {
        setPhase('ended');
        if (status === 'completed') {
          toast.success('Session completed');
          useNotificationStore.getState().addNotification({
            type: 'success',
            title: 'Session Completed',
            message: 'Agent evaluation session has ended.',
          });
        } else {
          toast.error('Session failed');
        }
      }
    });
    return unsubscribe;
  }, []);

  const handleStart = useCallback(async () => {
    if (!modelEndpoint || !judgeConfig) return;

    try {
      setEvalLoading(true);

      await createSession({
        name: `Agent Chat - ${modelEndpoint.name}`,
        mode: 'live',
        agent_config: {
          provider_id: modelEndpoint.provider_id,
          litellm_model: modelEndpoint.litellm_model,
          api_base: modelEndpoint.api_base,
          ...(systemPrompt.trim() && { system_prompt: systemPrompt.trim() }),
          ...(selectedEvaluatorId && { evaluator_id: selectedEvaluatorId }),
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
    setEvalLoading,
    createSession,
    connectWebSocket,
  ]);

  const handleEndSession = useCallback(async () => {
    try {
      await endSession();
      setPhase('ended');
      toast.success('Session ended');
    } catch {
      toast.error('Failed to end session');
    }
  }, [endSession]);

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
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <ProviderSelector value={modelEndpoint} onChange={setModelEndpoint} />
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

          {/* Connection lost banner */}
          {error && !isConnected && currentSession?.status === 'active' && (
            <div className="flex items-center justify-between rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2">
              <p className="text-sm text-destructive">{error}</p>
              <Button variant="outline" size="sm" onClick={handleReconnect}>
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                Reconnect
              </Button>
            </div>
          )}

          {/* Three-panel layout */}
          <div className="grid flex-1 gap-4 md:grid-cols-3" style={{ minHeight: '500px' }}>
            <ConversationPanel
              messages={messages}
              isProcessing={isProcessing}
              onSend={sendMessage}
              disabled={!isConnected}
            />
            <ToolInspector toolCalls={toolCalls} />
            <ScoringPanel scores={scores} isSessionEnded={false} />
          </div>
        </>
      )}

      {/* Ended Phase */}
      {phase === 'ended' && (
        <>
          <div className="grid gap-4 md:grid-cols-3" style={{ minHeight: '400px' }}>
            <ConversationPanel
              messages={messages}
              isProcessing={false}
              onSend={() => {}}
              disabled={true}
            />
            <ToolInspector toolCalls={toolCalls} />
            <ScoringPanel scores={scores} isSessionEnded={true} />
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
