import { useState, useMemo, useCallback } from 'react';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { RAGEndpointConfig } from '@/components/evaluation/RAGEndpointConfig';
import type { RAGEndpointSettings } from '@/types';
import { RAGMetricsSelector, ALL_RAG_METRICS } from '@/components/evaluation/RAGMetricsSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { RAGResultsTable } from '@/components/evaluation/RAGResultsTable';
import { RAGResultDetailDrawer } from '@/components/evaluation/RAGResultDetailDrawer';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationRun } from '@/hooks/useEvaluationRun';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import { api } from '@/services/api';
import type {
  JudgeReference,
  Result,
  CreateEvaluationRequest,
  LLMParams,
  DatasetItem,
} from '@/types';

export default function RAGEvaluation() {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [ragEndpoint, setRagEndpoint] = useState<RAGEndpointSettings>();
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(ALL_RAG_METRICS);
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
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
    useEvaluationRun({ mode: 'rag', onCompleted });

  const itemMap = useMemo(() => {
    const map = new Map<string, DatasetItem>();
    datasetItems.forEach((item) => map.set(item.id, item));
    return map;
  }, [datasetItems]);

  const isRagEndpointValid = (() => {
    if (!ragEndpoint) return false;
    if (ragEndpoint.backend_type === 'pgvector') {
      return Boolean(ragEndpoint.connection_string && ragEndpoint.table_name);
    }
    return Boolean(ragEndpoint.endpoint_url);
  })();

  const isConfigValid = Boolean(
    selectedDatasetId &&
    isRagEndpointValid &&
    judgeConfig &&
    selectedMetrics.length > 0 &&
    selectedEvaluatorId,
  );

  const handleStart = async () => {
    if (!selectedDatasetId || !ragEndpoint || !judgeConfig || !isRagEndpointValid) return;

    const evalName =
      ragEndpoint.backend_type === 'pgvector'
        ? `RAG Eval - pgvector:${ragEndpoint.table_name ?? ''}`
        : `RAG Eval - ${ragEndpoint.endpoint_url ?? ''}`;

    const modelApiBase =
      ragEndpoint.backend_type === 'pgvector' ? undefined : ragEndpoint.endpoint_url;

    const request: CreateEvaluationRequest = {
      name: evalName,
      mode: 'rag',
      dataset_id: selectedDatasetId,
      config: {
        model_endpoint: {
          name: 'RAG Endpoint',
          default_model: 'rag',
          api_base: modelApiBase,
        },
        judge_config: judgeConfig,
        evaluator_id: selectedEvaluatorId ?? undefined,
        rag_endpoint: ragEndpoint,
        rag_metrics: selectedMetrics,
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
    setRagEndpoint(undefined);
    setSelectedMetrics(ALL_RAG_METRICS);
    setJudgeConfig(undefined);
    setJudgeParams({});
    setSelectedResult(null);
    setDrawerOpen(false);
    setDatasetItems([]);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">RAG Pipeline Evaluation</h1>
        <p className="text-muted-foreground">
          Evaluate retrieval-augmented generation with chunk-level analysis of retrieval quality and
          answer generation.
        </p>
      </div>
      <Separator />

      {phase === 'configure' && (
        <>
          <EvaluatorSelector mode="rag" />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="text-sm font-medium">Dataset</h2>
                <DatasetSelector value={selectedDatasetId} onChange={setSelectedDatasetId} />
              </div>
              <RAGEndpointConfig value={ragEndpoint} onChange={setRagEndpoint} />
            </div>
            <div className="space-y-4">
              <RAGMetricsSelector value={selectedMetrics} onChange={setSelectedMetrics} />
              <JudgeConfigPanel value={judgeConfig} onChange={setJudgeConfig} />
            </div>
          </div>
          <LLMParamsPanel label="Judge Parameters" value={judgeParams} onChange={setJudgeParams} />
          <Button
            className="w-full"
            disabled={!isConfigValid || isLoading}
            onClick={() => void handleStart()}
          >
            {isLoading ? 'Starting...' : 'Start RAG Evaluation'}
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
          <RAGResultsTable
            results={results}
            datasetItems={datasetItems}
            onRowClick={handleRowClick}
          />

          <RAGResultDetailDrawer
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
