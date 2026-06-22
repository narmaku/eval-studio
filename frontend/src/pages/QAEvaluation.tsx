import { useState, useMemo, useCallback } from 'react';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { ProviderSelector } from '@/components/evaluation/ProviderSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { QAResultsTable } from '@/components/evaluation/QAResultsTable';
import { ResultDetailDrawer } from '@/components/evaluation/ResultDetailDrawer';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationRun } from '@/hooks/useEvaluationRun';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import { api } from '@/services/api';
import type {
  ModelEndpoint,
  JudgeReference,
  Result,
  CreateEvaluationRequest,
  LLMParams,
  DatasetItem,
} from '@/types';

export default function QAEvaluation() {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [modelEndpoint, setModelEndpoint] = useState<ModelEndpoint>();
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [modelParams, setModelParams] = useState<LLMParams>({});
  const [judgeParams, setJudgeParams] = useState<LLMParams>({});
  const [selectedResult, setSelectedResult] = useState<Result | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [datasetItems, setDatasetItems] = useState<DatasetItem[]>([]);

  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results, fetchAggregateMetrics } = useResultStore();

  const onCompleted = useCallback(
    (evaluationId: string) => {
      void fetchAggregateMetrics(evaluationId);
      if (selectedDatasetId) {
        api
          .getDataset(selectedDatasetId)
          .then((detail) => setDatasetItems(detail.items))
          .catch(() => setDatasetItems([]));
      }
    },
    [fetchAggregateMetrics, selectedDatasetId],
  );

  const { phase, currentEvaluation, isLoading, start, handleComplete, cancel, reset } =
    useEvaluationRun({ mode: 'qa', onCompleted });

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

    await start(request);
  };

  const handleRowClick = (result: Result) => {
    setSelectedResult(result);
    setDrawerOpen(true);
  };

  const handleNewEvaluation = () => {
    reset();
    setSelectedDatasetId(undefined);
    setModelEndpoint(undefined);
    setJudgeConfig(undefined);
    setModelParams({});
    setJudgeParams({});
    setSelectedResult(null);
    setDrawerOpen(false);
    setDatasetItems([]);
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
            {isLoading ? 'Starting...' : 'Start Evaluation'}
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
          <QAResultsTable
            results={results}
            datasetItems={datasetItems}
            onRowClick={handleRowClick}
          />

          <ResultDetailDrawer
            result={selectedResult}
            datasetItem={
              selectedResult?.dataset_item_id
                ? itemMap.get(selectedResult.dataset_item_id)
                : undefined
            }
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
