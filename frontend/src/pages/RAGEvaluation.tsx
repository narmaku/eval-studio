import { useState, useCallback } from 'react';
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
import type { JudgeReference, Result, CreateEvaluationRequest } from '@/types';

type PagePhase = 'configure' | 'running' | 'complete';

export default function RAGEvaluation() {
  const [phase, setPhase] = useState<PagePhase>('configure');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>();
  const [ragEndpoint, setRagEndpoint] = useState<RAGEndpointSettings>();
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(ALL_RAG_METRICS);
  const [judgeConfig, setJudgeConfig] = useState<JudgeReference>();
  const [selectedResult, setSelectedResult] = useState<Result | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { currentEvaluation, createAndRunEvaluation, setCurrentEvaluation, isLoading } =
    useEvaluationStore();
  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results, fetchResults } = useResultStore();

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
          litellm_model: 'rag',
          api_base: modelApiBase,
        },
        judge_config: judgeConfig,
        evaluator_id: selectedEvaluatorId ?? undefined,
        rag_endpoint: ragEndpoint,
        rag_metrics: selectedMetrics,
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
      setPhase('complete');
    } else if (evaluation?.status === 'failed') {
      toast.error('Evaluation failed');
      addNotification({
        type: 'error',
        title: 'RAG Evaluation Failed',
        message: `"${evaluation.name}" failed`,
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
  }, [fetchResults]);

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
    setSelectedResult(null);
    setDrawerOpen(false);
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
          <RAGResultsTable results={results} onRowClick={handleRowClick} />

          <RAGResultDetailDrawer
            result={selectedResult}
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
