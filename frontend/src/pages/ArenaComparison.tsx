import { useState, useCallback } from 'react';
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
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationRun } from '@/hooks/useEvaluationRun';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import { api } from '@/services/api';
import type {
  ModelEndpoint,
  JudgeReference,
  CreateEvaluationRequest,
  ArenaLeaderboardResponse,
  LLMParams,
} from '@/types';

export default function ArenaComparison() {
  const [contestants, setContestants] = useState<ModelEndpoint[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [modelParams, setModelParams] = useState<LLMParams>({});
  const [judgeParams, setJudgeParams] = useState<LLMParams>({});
  const [leaderboard, setLeaderboard] = useState<ArenaLeaderboardResponse | null>(null);

  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results } = useResultStore();

  const onCompleted = useCallback((evaluationId: string) => {
    void api
      .getArenaLeaderboard(evaluationId)
      .then(setLeaderboard)
      .catch(() => {
        // Leaderboard fetch failed — results will still show
      });
  }, []);

  const { phase, currentEvaluation, isLoading, start, handleComplete, cancel, reset } =
    useEvaluationRun({ mode: 'arena', onCompleted });

  const validContestants = contestants.filter((c) => c.name && (c.default_model || c.single_model));
  const isConfigValid = Boolean(
    validContestants.length >= 2 && selectedDatasetId && judgeConfig && selectedEvaluatorId,
  );

  const handleStart = async () => {
    if (!selectedDatasetId || !judgeConfig || validContestants.length < 2) return;

    const primaryEndpoint = validContestants[0]!;

    const request: CreateEvaluationRequest = {
      name: `Arena - ${validContestants.map((c) => c.name).join(' vs ')}`,
      mode: 'arena',
      dataset_id: selectedDatasetId,
      rubric_id: judgeConfig.rubric_id,
      config: {
        model_endpoint: primaryEndpoint,
        judge_config: judgeConfig,
        evaluator_id: selectedEvaluatorId ?? undefined,
        contestants: validContestants,
        ...(Object.keys(modelParams).length > 0 && { model_params: modelParams }),
        ...(Object.keys(judgeParams).length > 0 && { judge_params: judgeParams }),
      },
    };

    await start(request);
  };

  const handleNewArena = () => {
    reset();
    setContestants([]);
    setSelectedDatasetId(undefined);
    setJudgeConfig(undefined);
    setModelParams({});
    setJudgeParams({});
    setLeaderboard(null);
  };

  const contestantModels = validContestants.map((c) => c.default_model);

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
            <LLMParamsPanel
              label="Model Parameters"
              value={modelParams}
              onChange={setModelParams}
            />
            <LLMParamsPanel
              label="Judge Parameters"
              value={judgeParams}
              onChange={setJudgeParams}
            />
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

      {phase === 'running' && currentEvaluation && (
        <>
          <EvaluationProgress evaluationId={currentEvaluation.id} onComplete={handleComplete} />
          <Button variant="outline" onClick={cancel}>
            Cancel
          </Button>
        </>
      )}

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
              (c) => c.average_breakdown && Object.keys(c.average_breakdown).length >= 2,
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
