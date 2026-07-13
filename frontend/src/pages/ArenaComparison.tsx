import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Trophy, Play } from 'lucide-react';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { ContestantSelector } from '@/components/evaluation/ContestantSelector';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { ArenaLeaderboard } from '@/components/evaluation/ArenaLeaderboard';
import { ArenaResultsGrid } from '@/components/evaluation/ArenaResultsGrid';
import { ContestantScoreChart, RadarComparisonChart } from '@/components/results';
import { RunDetailsPanel } from '@/components/evaluation/RunDetailsPanel';
import {
  metadataEntriesToRecord,
  buildArenaAutoMetadata,
} from '@/components/evaluation/runDetailsUtils';
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
  const [runTitle, setRunTitle] = useState('');
  const [runDescription, setRunDescription] = useState('');
  const [runMetadata, setRunMetadata] = useState<{ key: string; value: string }[]>([]);

  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results } = useResultStore();

  const handleContestantsChange = useCallback(
    (newContestants: ModelEndpoint[]) => {
      setContestants(newContestants);
      const valid = newContestants.filter((c) => c.name && (c.default_model || c.single_model));
      if (valid.length > 0) {
        setRunMetadata(
          buildArenaAutoMetadata({
            contestantCount: valid.length,
            contestantModels: valid.map((c) => c.default_model),
            temperature: modelParams.temperature,
            topP: modelParams.top_p,
          }),
        );
      }
    },
    [modelParams.temperature, modelParams.top_p],
  );

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
    const autoName = `Arena - ${validContestants.map((c) => c.name).join(' vs ')}`;
    const effectiveName = runTitle.trim() || autoName;

    const request: CreateEvaluationRequest = {
      name: effectiveName,
      ...(runDescription.trim() && { description: runDescription.trim() }),
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
      metadata: metadataEntriesToRecord(runMetadata),
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
    setRunTitle('');
    setRunDescription('');
    setRunMetadata([]);
  };

  const contestantModels = validContestants.map((c) => c.default_model);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/evaluate"
          className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] text-text-2 hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All modes
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-mode-arena-bg text-mode-arena-fg">
            <Trophy className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-[22px] font-semibold tracking-[-0.02em]">Model Arena</h1>
            <p className="text-[13px] text-text-2">
              Run the same evaluation across multiple models side-by-side and rank by performance.
            </p>
          </div>
        </div>
      </div>

      {phase === 'configure' && (
        <>
          <EvaluatorSelector mode="qa" />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="text-[10.5px] font-semibold tracking-[0.06em] uppercase text-text-3">
                  Dataset
                </h2>
                <DatasetSelector value={selectedDatasetId} onChange={setSelectedDatasetId} />
              </div>
              <ContestantSelector value={contestants} onChange={handleContestantsChange} />
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
          <RunDetailsPanel
            title={runTitle}
            onTitleChange={setRunTitle}
            description={runDescription}
            onDescriptionChange={setRunDescription}
            metadata={runMetadata}
            onMetadataChange={setRunMetadata}
          />
          <button
            className="flex w-full items-center justify-center gap-2 rounded-[9px] bg-primary px-4 py-3 text-[13px] font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90 disabled:opacity-50"
            disabled={!isConfigValid || isLoading}
            onClick={() => void handleStart()}
          >
            <Play className="h-4 w-4" />
            {isLoading ? 'Starting...' : 'Start Arena'}
          </button>
        </>
      )}

      {phase === 'running' && currentEvaluation && (
        <>
          <EvaluationProgress evaluationId={currentEvaluation.id} onComplete={handleComplete} />
          <button
            className="rounded-[9px] border border-border px-4 py-2 text-[13px] font-medium text-text-2 transition-colors hover:bg-surface-3"
            onClick={cancel}
          >
            Cancel
          </button>
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

          <button
            className="rounded-[9px] border border-border px-4 py-2 text-[13px] font-medium text-text-2 transition-colors hover:bg-surface-3"
            onClick={handleNewArena}
          >
            New Arena
          </button>
        </>
      )}
    </div>
  );
}
