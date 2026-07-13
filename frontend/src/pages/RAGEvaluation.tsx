import { useState, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Database, Play } from 'lucide-react';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { RAGEndpointConfig } from '@/components/evaluation/RAGEndpointConfig';
import type { RAGEndpointSettings } from '@/types';
import { RAGMetricsSelector, ALL_RAG_METRICS } from '@/components/evaluation/RAGMetricsSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { RAGResultsTable } from '@/components/evaluation/RAGResultsTable';
import { RAGResultDetailDrawer } from '@/components/evaluation/RAGResultDetailDrawer';
import { RunDetailsPanel } from '@/components/evaluation/RunDetailsPanel';
import {
  metadataEntriesToRecord,
  buildRAGAutoMetadata,
} from '@/components/evaluation/runDetailsUtils';
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
  const [runTitle, setRunTitle] = useState('');
  const [runDescription, setRunDescription] = useState('');
  const [runMetadata, setRunMetadata] = useState<{ key: string; value: string }[]>([]);

  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results, fetchAggregateMetrics } = useResultStore();

  const handleRagEndpointChange = useCallback((endpoint: RAGEndpointSettings | undefined) => {
    setRagEndpoint(endpoint);
    if (endpoint) {
      setRunMetadata(
        buildRAGAutoMetadata({
          backendType: endpoint.backend_type,
          endpointUrl: endpoint.endpoint_url,
          tableName: endpoint.table_name,
          embeddingModel: endpoint.embedding_model,
          generatorProviderId: endpoint.generator_provider_id,
        }),
      );
    }
  }, []);

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

    const autoName =
      ragEndpoint.backend_type === 'pgvector'
        ? `RAG Eval - pgvector:${ragEndpoint.table_name ?? ''}`
        : `RAG Eval - ${ragEndpoint.endpoint_url ?? ''}`;

    const effectiveName = runTitle.trim() || autoName;

    const modelApiBase =
      ragEndpoint.backend_type === 'pgvector' ? undefined : ragEndpoint.endpoint_url;

    const request: CreateEvaluationRequest = {
      name: effectiveName,
      ...(runDescription.trim() && { description: runDescription.trim() }),
      mode: 'rag',
      dataset_id: selectedDatasetId,
      rubric_id: judgeConfig.rubric_id,
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
      metadata: metadataEntriesToRecord(runMetadata),
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
    setRunTitle('');
    setRunDescription('');
    setRunMetadata([]);
  };

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
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-mode-rag-bg text-mode-rag-fg">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-[22px] font-semibold tracking-[-0.02em]">
              RAG Pipeline Evaluation
            </h1>
            <p className="text-[13px] text-text-2">
              Evaluate retrieval-augmented generation with chunk-level analysis of retrieval quality
              and answer generation.
            </p>
          </div>
        </div>
      </div>

      {phase === 'configure' && (
        <>
          <EvaluatorSelector mode="rag" />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <h2 className="text-[10.5px] font-semibold tracking-[0.06em] uppercase text-text-3">
                  Dataset
                </h2>
                <DatasetSelector value={selectedDatasetId} onChange={setSelectedDatasetId} />
              </div>
              <RAGEndpointConfig value={ragEndpoint} onChange={handleRagEndpointChange} />
            </div>
            <div className="space-y-4">
              <RAGMetricsSelector value={selectedMetrics} onChange={setSelectedMetrics} />
              <JudgeConfigPanel value={judgeConfig} onChange={setJudgeConfig} />
            </div>
          </div>
          <LLMParamsPanel label="Judge Parameters" value={judgeParams} onChange={setJudgeParams} />
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
            {isLoading ? 'Starting...' : 'Start RAG Evaluation'}
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

          <button
            className="rounded-[9px] border border-border px-4 py-2 text-[13px] font-medium text-text-2 transition-colors hover:bg-surface-3"
            onClick={handleNewEvaluation}
          >
            New Evaluation
          </button>
        </>
      )}
    </div>
  );
}
