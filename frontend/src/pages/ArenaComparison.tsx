import { useState, useCallback } from 'react';
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
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { api } from '@/services/api';
import type {
  ModelEndpoint,
  JudgeReference,
  CreateEvaluationRequest,
  ArenaLeaderboardResponse,
} from '@/types';

type PagePhase = 'configure' | 'running' | 'complete';

export default function ArenaComparison() {
  const [phase, setPhase] = useState<PagePhase>('configure');
  const [contestants, setContestants] = useState<ModelEndpoint[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [leaderboard, setLeaderboard] = useState<ArenaLeaderboardResponse | null>(null);

  const { currentEvaluation, createAndRunEvaluation, setCurrentEvaluation, isLoading } =
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
    const primaryEndpoint = validContestants[0];

    const request: CreateEvaluationRequest = {
      name: `Arena - ${validContestants.map((c) => c.name).join(' vs ')}`,
      mode: 'arena',
      dataset_id: selectedDatasetId,
      config: {
        model_endpoint: primaryEndpoint,
        judge_config: judgeConfig,
        evaluator_id: selectedEvaluatorId ?? undefined,
        contestants: validContestants,
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
      void api.getArenaLeaderboard(evaluation.id).then(setLeaderboard).catch(() => {
        // Leaderboard fetch failed — results will still show
      });
      setPhase('complete');
    } else if (evaluation?.status === 'failed') {
      toast.error('Arena failed');
      addNotification({
        type: 'error',
        title: 'Arena Failed',
        message: `"${evaluation.name}" failed`,
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
                <DatasetSelector
                  value={selectedDatasetId}
                  onChange={setSelectedDatasetId}
                />
              </div>
              <ContestantSelector
                value={contestants}
                onChange={setContestants}
              />
            </div>
            <div>
              <JudgeConfigPanel
                value={judgeConfig}
                onChange={setJudgeConfig}
              />
            </div>
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
          <EvaluationProgress
            evaluationId={currentEvaluation.id}
            onComplete={handleComplete}
          />
          <Button
            variant="outline"
            onClick={() => {
              setCurrentEvaluation(null);
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
          {leaderboard && <ArenaLeaderboard leaderboard={leaderboard} />}

          <ArenaResultsGrid
            results={results}
            contestants={contestantModels}
          />

          <Button variant="outline" onClick={handleNewArena}>
            New Arena
          </Button>
        </>
      )}
    </div>
  );
}
