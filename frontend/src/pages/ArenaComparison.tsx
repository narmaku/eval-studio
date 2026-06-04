import { useState, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { ContestantSelector } from '@/components/evaluation/ContestantSelector';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { ArenaLeaderboard } from '@/components/evaluation/ArenaLeaderboard';
import { ArenaResultsGrid } from '@/components/evaluation/ArenaResultsGrid';
import { ContestantScoreChart, RadarComparisonChart } from '@/components/results';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { api } from '@/services/api';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import type {
  ModelEndpoint,
  JudgeReference,
  CreateEvaluationRequest,
  ArenaLeaderboardResponse,
  LLMParams,
} from '@/types';

type PagePhase = 'configure' | 'running' | 'complete';

function getInitialPhase(): PagePhase {
  try {
    const stored = sessionStorage.getItem('runningEvaluation');
    if (stored) {
      const running = JSON.parse(stored) as { mode: string };
      if (running.mode === 'arena') return 'running';
    }
  } catch {
    // ignore
  }
  return 'configure';
}

export default function ArenaComparison() {
  const [phase, setPhase] = useState<PagePhase>(getInitialPhase);

  // Auto-resume running evaluation from sessionStorage
  const { getRunningEvaluation, setCurrentEvaluation: setCurrentEval } = useEvaluationStore();
  useEffect(() => {
    const running = getRunningEvaluation();
    if (running && running.mode === 'arena') {
      setCurrentEval({
        id: running.id,
        name: running.name,
        mode: running.mode,
      } as Parameters<typeof setCurrentEval>[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [contestants, setContestants] = useState<ModelEndpoint[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [modelParams, setModelParams] = useState<LLMParams>({});
  const [judgeParams, setJudgeParams] = useState<LLMParams>({});
  const [leaderboard, setLeaderboard] = useState<ArenaLeaderboardResponse | null>(null);

  const { currentEvaluation, createAndRunEvaluation, setCurrentEvaluation, isLoading, clearRunningEvaluation, clearLogs } =
    useEvaluationStore();
  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results, fetchResults } = useResultStore();

  // Need at least 2 contestants with valid model config
  const validContestants = contestants.filter((c) => c.name && c.litellm_model);
  const isConfigValid = Boolean(
    validContestants.length >= 2 && selectedDatasetId && judgeConfig && selectedEvaluatorId,
  );

  const handleStart = async () => {
    if (!selectedDatasetId || !judgeConfig || validContestants.length < 2) return;

    // Use the first contestant as the primary model_endpoint (required by API)
    // and pass all contestants in the config
    const primaryEndpoint = validContestants[0]!;

    const request: CreateEvaluationRequest = {
      name: `Arena - ${validContestants.map((c) => c.name).join(' vs ')}`,
      mode: 'arena',
      dataset_id: selectedDatasetId,
      config: {
        model_endpoint: primaryEndpoint,
        judge_config: judgeConfig,
        evaluator_id: selectedEvaluatorId ?? undefined,
        contestants: validContestants,
        ...(Object.keys(modelParams).length > 0 && { model_params: modelParams }),
        ...(Object.keys(judgeParams).length > 0 && { judge_params: judgeParams }),
      },
    };

    try {
      await createAndRunEvaluation(request);
      toast.success('Arena started');
      setPhase('running');
    } catch (err) {
      toast.error('Failed to start arena');
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Failed to Start Arena',
        message: err instanceof Error ? err.message : 'An unknown error occurred',
        details: err instanceof Error ? err.stack : undefined,
      });
    }
  };

  const handleComplete = useCallback(() => {
    const evaluation = useEvaluationStore.getState().currentEvaluation;
    const addNotification = useNotificationStore.getState().addNotification;

    if (evaluation?.status === 'completed') {
      toast.success('Arena completed');
      addNotification({
        type: 'success',
        title: 'Arena Completed',
        message: `"${evaluation.name}" finished successfully`,
        evaluationId: evaluation.id,
      });
      void fetchResults(evaluation.id);
      void api
        .getArenaLeaderboard(evaluation.id)
        .then(setLeaderboard)
        .catch(() => {
          // Leaderboard fetch failed — results will still show
        });
      setPhase('complete');
    } else if (evaluation?.status === 'failed') {
      const errorMsg = evaluation.error || 'Unknown error';
      toast.error(`Arena failed: ${errorMsg}`);
      addNotification({
        type: 'error',
        title: 'Arena Failed',
        message: `"${evaluation.name}" failed: ${errorMsg}`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    } else if (evaluation?.status === 'cancelled') {
      toast('Arena was cancelled');
      addNotification({
        type: 'warning',
        title: 'Arena Cancelled',
        message: `"${evaluation.name}" was cancelled`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    }
  }, [fetchResults]);

  const handleNewArena = () => {
    setPhase('configure');
    setContestants([]);
    setSelectedDatasetId(undefined);
    setJudgeConfig(undefined);
    setModelParams({});
    setJudgeParams({});
    setLeaderboard(null);
    useEvaluatorStore.getState().resetSelection();
  };

  // Extract unique contestant model names for the results grid
  const contestantModels = validContestants.map((c) => c.litellm_model);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Model Arena</h1>
        <p className="text-muted-foreground">
          Compare multiple models by running the same evaluation across all contestants
          side-by-side.
        </p>
      </div>
      <Separator />

      {/* Configure Phase */}
      {phase === 'configure' && (
        <>
          <EvaluatorSelector mode="qa" />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="text-sm font-medium">Dataset</h2>
                <DatasetSelector value={selectedDatasetId} onChange={setSelectedDatasetId} />
              </div>
              <ContestantSelector value={contestants} onChange={setContestants} />
            </div>
            <div className="space-y-4">
              <JudgeConfigPanel value={judgeConfig} onChange={setJudgeConfig} />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <LLMParamsPanel label="Model Parameters" value={modelParams} onChange={setModelParams} />
            <LLMParamsPanel label="Judge Parameters" value={judgeParams} onChange={setJudgeParams} />
          </div>
          <Button
            className="w-full"
            disabled={!isConfigValid || isLoading}
            onClick={() => void handleStart()}
          >
            {isLoading ? 'Starting...' : 'Start Arena'}
          </Button>
        </>
      )}

      {/* Running Phase */}
      {phase === 'running' && currentEvaluation && (
        <>
          <EvaluationProgress evaluationId={currentEvaluation.id} onComplete={handleComplete} />
          <Button
            variant="outline"
            onClick={() => {
              setCurrentEvaluation(null);
              clearRunningEvaluation();
              clearLogs();
              setPhase('configure');
              toast('Arena cancelled');
            }}
          >
            Cancel
          </Button>
        </>
      )}

      {/* Complete Phase */}
      {phase === 'complete' && (
        <>
          {leaderboard && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <ArenaLeaderboard leaderboard={leaderboard} />
              <ContestantScoreChart contestants={leaderboard.contestants} />
            </div>
          )}

          {leaderboard &&
            leaderboard.contestants.some(
              (c) =>
                c.average_breakdown && Object.keys(c.average_breakdown).length >= 2,
            ) && (
              <RadarComparisonChart
                series={leaderboard.contestants
                  .filter((c) => c.average_breakdown)
                  .map((c) => ({
                    name: c.contestant_model,
                    data: c.average_breakdown!,
                  }))}
                title="Per-Metric Comparison"
              />
            )}

          <ArenaResultsGrid
            results={results}
            contestants={contestantModels}
            datasetId={selectedDatasetId}
          />

          <Button variant="outline" onClick={handleNewArena}>
            New Arena
          </Button>
        </>
      )}
    </div>
  );
}
