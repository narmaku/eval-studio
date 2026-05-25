import { useState, useCallback, useMemo } from 'react';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { ModelEndpointConfig } from '@/components/evaluation/ModelEndpointConfig';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { QAResultsTable } from '@/components/evaluation/QAResultsTable';
import { AggregateStats } from '@/components/evaluation/AggregateStats';
import { ResultDetailDrawer } from '@/components/evaluation/ResultDetailDrawer';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useResultStore } from '@/stores/resultStore';
import type {
  ModelEndpoint,
  JudgeReference,
  Score,
  CreateEvaluationRequest,
} from '@/types';

type PagePhase = 'configure' | 'running' | 'complete';

export default function QAEvaluation() {
  const [phase, setPhase] = useState<PagePhase>('configure');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [modelEndpoint, setModelEndpoint] = useState<ModelEndpoint>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [selectedScore, setSelectedScore] = useState<Score | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { currentEvaluation, createAndRunEvaluation, isLoading } = useEvaluationStore();
  const { results, fetchResults } = useResultStore();

  const isConfigValid = Boolean(selectedDatasetId && modelEndpoint && judgeConfig);

  const handleStart = async () => {
    if (!selectedDatasetId || !modelEndpoint || !judgeConfig) return;

    const request: CreateEvaluationRequest = {
      name: `Q&A Eval - ${modelEndpoint.name}`,
      mode: 'qa',
      dataset_id: selectedDatasetId,
      config: {
        model_endpoint: modelEndpoint,
        judge_config: judgeConfig,
      },
    };

    try {
      await createAndRunEvaluation(request);
      toast.success('Evaluation started');
      setPhase('running');
    } catch {
      toast.error('Failed to start evaluation');
    }
  };

  const handleComplete = useCallback(() => {
    const evaluation = useEvaluationStore.getState().currentEvaluation;
    if (evaluation?.status === 'completed') {
      toast.success('Evaluation completed');
      void fetchResults(evaluation.id);
      setPhase('complete');
    } else if (evaluation?.status === 'failed') {
      toast.error(`Evaluation failed: ${evaluation.error ?? 'Unknown error'}`);
      setPhase('configure');
    }
  }, [fetchResults]);

  const handleRowClick = (score: Score) => {
    setSelectedScore(score);
    setDrawerOpen(true);
  };

  const handleNewEvaluation = () => {
    setPhase('configure');
    setSelectedDatasetId(undefined);
    setModelEndpoint(undefined);
    setJudgeConfig(undefined);
    setSelectedScore(null);
    setDrawerOpen(false);
  };

  // Collect all scores from all results
  const allScores = useMemo(() => {
    return results.flatMap((r) => r.scores);
  }, [results]);

  // Use first result's aggregate metrics if available
  const aggregateMetrics = results[0]?.aggregate_metrics;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Q&A Evaluation</h1>
        <p className="text-muted-foreground">
          Single-turn question-and-answer evaluation with configurable judges and scoring metrics.
        </p>
      </div>
      <Separator />

      {/* Configure Phase */}
      {phase === 'configure' && (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="text-sm font-medium">Dataset</h2>
                <DatasetSelector
                  value={selectedDatasetId}
                  onChange={setSelectedDatasetId}
                />
              </div>
              <ModelEndpointConfig
                value={modelEndpoint}
                onChange={setModelEndpoint}
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
            {isLoading ? 'Starting...' : 'Start Evaluation'}
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
              setPhase('configure');
              toast('Evaluation cancelled');
            }}
          >
            Cancel
          </Button>
        </>
      )}

      {/* Complete Phase */}
      {phase === 'complete' && (
        <>
          {aggregateMetrics && <AggregateStats metrics={aggregateMetrics} />}

          <QAResultsTable
            scores={allScores}
            onRowClick={handleRowClick}
          />

          <ResultDetailDrawer
            score={selectedScore}
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
          />

          <Button variant="outline" onClick={handleNewEvaluation}>
            New Evaluation
          </Button>
        </>
      )}
    </div>
  );
}
