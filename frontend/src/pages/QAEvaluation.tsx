import { useState, useCallback, useEffect, useMemo } from 'react';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { ProviderSelector } from '@/components/evaluation/ProviderSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { QAResultsTable } from '@/components/evaluation/QAResultsTable';
import { ResultDetailDrawer } from '@/components/evaluation/ResultDetailDrawer';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import { api } from '@/services/api';
import type { ModelEndpoint, JudgeReference, Result, CreateEvaluationRequest, LLMParams, DatasetItem } from '@/types';

type PagePhase = 'configure' | 'running' | 'complete';

function getInitialPhase(): PagePhase {
  try {
    const stored = sessionStorage.getItem('runningEvaluation');
    if (stored) {
      const running = JSON.parse(stored) as { mode: string };
      if (running.mode === 'qa') return 'running';
    }
  } catch {
    // ignore
  }
  return 'configure';
}

export default function QAEvaluation() {
  const [phase, setPhase] = useState<PagePhase>(getInitialPhase);

  // Auto-resume running evaluation from sessionStorage
  const { getRunningEvaluation, setCurrentEvaluation: setCurrentEval } = useEvaluationStore();
  useEffect(() => {
    const running = getRunningEvaluation();
    if (running && running.mode === 'qa') {
      setCurrentEval({
        id: running.id,
        name: running.name,
        mode: running.mode,
      } as Parameters<typeof setCurrentEval>[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [modelEndpoint, setModelEndpoint] = useState<ModelEndpoint>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [modelParams, setModelParams] = useState<LLMParams>({});
  const [judgeParams, setJudgeParams] = useState<LLMParams>({});
  const [selectedResult, setSelectedResult] = useState<Result | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [datasetItems, setDatasetItems] = useState<DatasetItem[]>([]);

  const { currentEvaluation, createAndRunEvaluation, setCurrentEvaluation, isLoading, clearRunningEvaluation, clearLogs } =
    useEvaluationStore();
  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results, fetchResults, fetchAggregateMetrics } = useResultStore();

  const itemMap = useMemo(() => {
    const map = new Map<string, DatasetItem>();
    datasetItems.forEach((item) => map.set(item.id, item));
    return map;
  }, [datasetItems]);

  const isConfigValid = Boolean(
    selectedDatasetId && modelEndpoint && judgeConfig && selectedEvaluatorId,
  );

  const handleStart = async () => {
    if (!selectedDatasetId || !modelEndpoint || !judgeConfig) return;

    const request: CreateEvaluationRequest = {
      name: `Q&A Eval - ${modelEndpoint.name}`,
      mode: 'qa',
      dataset_id: selectedDatasetId,
      config: {
        model_endpoint: modelEndpoint,
        judge_config: judgeConfig,
        evaluator_id: selectedEvaluatorId ?? undefined,
        ...(Object.keys(modelParams).length > 0 && { model_params: modelParams }),
        ...(Object.keys(judgeParams).length > 0 && { judge_params: judgeParams }),
      },
    };

    try {
      await createAndRunEvaluation(request);
      toast.success('Evaluation started');
      setPhase('running');
    } catch (err) {
      toast.error('Failed to start evaluation');
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Failed to Start Evaluation',
        message: err instanceof Error ? err.message : 'An unknown error occurred',
        details: err instanceof Error ? err.stack : undefined,
      });
    }
  };

  const handleComplete = useCallback(() => {
    const evaluation = useEvaluationStore.getState().currentEvaluation;
    const addNotification = useNotificationStore.getState().addNotification;

    if (evaluation?.status === 'completed') {
      toast.success('Evaluation completed');
      addNotification({
        type: 'success',
        title: 'Evaluation Completed',
        message: `"${evaluation.name}" finished successfully`,
        evaluationId: evaluation.id,
      });
      void fetchResults(evaluation.id, 1, 100);
      void fetchAggregateMetrics(evaluation.id);
      if (selectedDatasetId) {
        api.getDataset(selectedDatasetId)
          .then((detail) => setDatasetItems(detail.items))
          .catch(() => setDatasetItems([]));
      }
      setPhase('complete');
    } else if (evaluation?.status === 'failed') {
      const errorMsg = evaluation.error || 'Unknown error';
      toast.error(`Evaluation failed: ${errorMsg}`);
      addNotification({
        type: 'error',
        title: 'Evaluation Failed',
        message: `"${evaluation.name}" failed: ${errorMsg}`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    } else if (evaluation?.status === 'cancelled') {
      toast('Evaluation was cancelled');
      addNotification({
        type: 'warning',
        title: 'Evaluation Cancelled',
        message: `"${evaluation.name}" was cancelled`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    }
  }, [fetchResults, fetchAggregateMetrics, selectedDatasetId]);

  const handleRowClick = (result: Result) => {
    setSelectedResult(result);
    setDrawerOpen(true);
  };

  const handleNewEvaluation = () => {
    setPhase('configure');
    setSelectedDatasetId(undefined);
    setModelEndpoint(undefined);
    setJudgeConfig(undefined);
    setModelParams({});
    setJudgeParams({});
    setSelectedResult(null);
    setDrawerOpen(false);
    setDatasetItems([]);
    useEvaluatorStore.getState().resetSelection();
  };

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
          <EvaluatorSelector mode="qa" />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="text-sm font-medium">Dataset</h2>
                <DatasetSelector value={selectedDatasetId} onChange={setSelectedDatasetId} />
              </div>
              <ProviderSelector value={modelEndpoint} onChange={setModelEndpoint} />
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
            {isLoading ? 'Starting...' : 'Start Evaluation'}
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
          <QAResultsTable results={results} datasetItems={datasetItems} onRowClick={handleRowClick} />

          <ResultDetailDrawer
            result={selectedResult}
            datasetItem={selectedResult?.dataset_item_id ? itemMap.get(selectedResult.dataset_item_id) : undefined}
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
