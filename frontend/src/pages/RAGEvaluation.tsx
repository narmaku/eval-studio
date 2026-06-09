import { useState, useCallback, useEffect, useMemo } from 'react';
import { toast } from 'sonner';
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
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import { api } from '@/services/api';
import type { JudgeReference, Result, CreateEvaluationRequest, LLMParams, DatasetItem } from '@/types';

type PagePhase = 'configure' | 'running' | 'complete';

function getInitialPhase(): PagePhase {
  try {
    const stored = sessionStorage.getItem('runningEvaluation');
    if (stored) {
      const running = JSON.parse(stored) as { mode: string };
      if (running.mode === 'rag') return 'running';
    }
  } catch {
    // ignore
  }
  return 'configure';
}

export default function RAGEvaluation() {
  const [phase, setPhase] = useState<PagePhase>(getInitialPhase);

  // Auto-resume running evaluation from sessionStorage
  const { getRunningEvaluation, setCurrentEvaluation: setCurrentEval } = useEvaluationStore();
  useEffect(() => {
    const running = getRunningEvaluation();
    if (running && running.mode === 'rag') {
      setCurrentEval({
        id: running.id,
        name: running.name,
        mode: running.mode,
      } as Parameters<typeof setCurrentEval>[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [ragEndpoint, setRagEndpoint] = useState<RAGEndpointSettings>();
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(ALL_RAG_METRICS);
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [judgeParams, setJudgeParams] = useState<LLMParams>({});
  const [selectedResult, setSelectedResult] = useState<Result | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [datasetItems, setDatasetItems] = useState<DatasetItem[]>([]);

  const { currentEvaluation, createAndRunEvaluation, setCurrentEvaluation, isLoading, clearRunningEvaluation, clearLogs } =
    useEvaluationStore();
  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results, fetchResults } = useResultStore();

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

    try {
      await createAndRunEvaluation(request);
      toast.success('RAG evaluation started');
      setPhase('running');
    } catch (err) {
      toast.error('Failed to start evaluation');
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Failed to Start RAG Evaluation',
        message: err instanceof Error ? err.message : 'An unknown error occurred',
        details: err instanceof Error ? err.stack : undefined,
      });
    }
  };

  const handleComplete = useCallback(() => {
    const evaluation = useEvaluationStore.getState().currentEvaluation;
    const addNotification = useNotificationStore.getState().addNotification;

    if (evaluation?.status === 'completed') {
      toast.success('RAG evaluation completed');
      addNotification({
        type: 'success',
        title: 'RAG Evaluation Completed',
        message: `"${evaluation.name}" finished successfully`,
        evaluationId: evaluation.id,
      });
      void fetchResults(evaluation.id);
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
        title: 'RAG Evaluation Failed',
        message: `"${evaluation.name}" failed: ${errorMsg}`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    } else if (evaluation?.status === 'cancelled') {
      toast('Evaluation was cancelled');
      addNotification({
        type: 'warning',
        title: 'RAG Evaluation Cancelled',
        message: `"${evaluation.name}" was cancelled`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    }
  }, [fetchResults, selectedDatasetId]);

  const handleRowClick = (result: Result) => {
    setSelectedResult(result);
    setDrawerOpen(true);
  };

  const handleNewEvaluation = () => {
    setPhase('configure');
    setSelectedDatasetId(undefined);
    setRagEndpoint(undefined);
    setSelectedMetrics(ALL_RAG_METRICS);
    setJudgeConfig(undefined);
    setJudgeParams({});
    setSelectedResult(null);
    setDrawerOpen(false);
    setDatasetItems([]);
    useEvaluatorStore.getState().resetSelection();
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

      {/* Configure Phase */}
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
          <RAGResultsTable results={results} datasetItems={datasetItems} onRowClick={handleRowClick} />

          <RAGResultDetailDrawer
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
