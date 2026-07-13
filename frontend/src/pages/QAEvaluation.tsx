import { useState, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, MessageSquare, Play } from 'lucide-react';
import { EvaluatorSelector } from '@/components/evaluation/EvaluatorSelector';
import { DatasetSelector } from '@/components/evaluation/DatasetSelector';
import { ProviderSelector } from '@/components/evaluation/ProviderSelector';
import { JudgeConfigPanel } from '@/components/evaluation/JudgeConfigPanel';
import { EvaluationProgress } from '@/components/evaluation/EvaluationProgress';
import { QAResultsTable } from '@/components/evaluation/QAResultsTable';
import { ResultDetailDrawer } from '@/components/evaluation/ResultDetailDrawer';
import { RunDetailsPanel } from '@/components/evaluation/RunDetailsPanel';
import {
  metadataEntriesToRecord,
  buildAutoMetadata,
} from '@/components/evaluation/runDetailsUtils';
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
  const [runTitle, setRunTitle] = useState('');
  const [runDescription, setRunDescription] = useState('');
  const [runMetadata, setRunMetadata] = useState<{ key: string; value: string }[]>([]);

  const { selectedEvaluatorId } = useEvaluatorStore();
  const { results, fetchAggregateMetrics } = useResultStore();

  const handleModelEndpointChange = useCallback(
    (endpoint: ModelEndpoint | undefined) => {
      setModelEndpoint(endpoint);
      if (endpoint) {
        setRunMetadata(
          buildAutoMetadata({
            providerName: endpoint.provider_id ?? endpoint.name,
            modelName: endpoint.default_model,
            temperature: modelParams.temperature,
            topP: modelParams.top_p,
          }),
        );
      }
    },
    [modelParams.temperature, modelParams.top_p],
  );

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

    const effectiveName = runTitle.trim() || `Q&A Eval - ${modelEndpoint.name}`;

    const request: CreateEvaluationRequest = {
      name: effectiveName,
      ...(runDescription.trim() && { description: runDescription.trim() }),
      mode: 'qa',
      dataset_id: selectedDatasetId,
      rubric_id: judgeConfig.rubric_id,
      config: {
        model_endpoint: modelEndpoint,
        judge_config: judgeConfig,
        evaluator_id: selectedEvaluatorId ?? undefined,
        ...(Object.keys(modelParams).length > 0 && { model_params: modelParams }),
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
    setModelEndpoint(undefined);
    setJudgeConfig(undefined);
    setModelParams({});
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
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-mode-qa-bg text-mode-qa-fg">
            <MessageSquare className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-[22px] font-semibold tracking-[-0.02em]">Q&A Evaluation</h1>
            <p className="text-[13px] text-text-2">
              Single-turn question-and-answer evaluation with configurable judges and scoring
              metrics.
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
              <ProviderSelector value={modelEndpoint} onChange={handleModelEndpointChange} />
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
            {isLoading ? 'Starting...' : 'Start Evaluation'}
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
