import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { ArtifactsList, ResultDetailView } from '@/components/results';
import { api } from '@/services/api';
import type { DatasetItem, ArenaLeaderboardResponse } from '@/types';

export default function ResultDetail() {
  const { resultId } = useParams<{ resultId: string }>();
  const {
    results,
    isLoading,
    error,
    pagination,
    aggregateMetrics,
    fetchResults,
    fetchAggregateMetrics,
    fetchAllResultsForExport,
  } = useResultStore();
  const { evaluations, fetchEvaluations } = useEvaluationStore();
  const [datasetItems, setDatasetItems] = useState<DatasetItem[]>([]);
  const [arenaLeaderboard, setArenaLeaderboard] = useState<ArenaLeaderboardResponse | null>(null);

  useEffect(() => {
    if (resultId) {
      void fetchResults(resultId);
      void fetchAggregateMetrics(resultId);
      void fetchEvaluations();
    }
  }, [resultId, fetchResults, fetchAggregateMetrics, fetchEvaluations]);

  const evaluation = evaluations.find((e) => e.id === resultId);

  useEffect(() => {
    if (evaluation?.dataset_id) {
      api
        .getDataset(evaluation.dataset_id)
        .then((detail) => setDatasetItems(detail.items))
        .catch(() => setDatasetItems([]));
    }
  }, [evaluation?.dataset_id]);

  useEffect(() => {
    if (evaluation?.mode === 'arena' && resultId) {
      api
        .getArenaLeaderboard(resultId)
        .then(setArenaLeaderboard)
        .catch(() => setArenaLeaderboard(null));
    }
  }, [evaluation?.mode, resultId]);

  const handlePageChange = useCallback(
    (page: number) => {
      if (resultId) {
        void fetchResults(resultId, page, pagination?.page_size ?? 20);
      }
    },
    [resultId, pagination?.page_size, fetchResults],
  );

  const handlePageSizeChange = useCallback(
    (size: number) => {
      if (resultId) {
        void fetchResults(resultId, 1, size);
      }
    },
    [resultId, fetchResults],
  );

  const handleFetchAllForExport = useCallback(() => {
    if (!resultId) return Promise.resolve([]);
    return fetchAllResultsForExport(resultId);
  }, [resultId, fetchAllResultsForExport]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading result details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-destructive font-medium">Error loading result</p>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">No results found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ResultDetailView
        results={results}
        aggregateMetrics={aggregateMetrics}
        evaluation={evaluation}
        evaluationName={evaluation?.name}
        evaluationMode={evaluation?.mode}
        evaluationConfig={evaluation?.config}
        evaluationMetadata={evaluation?.metadata}
        datasetItems={datasetItems}
        arenaLeaderboard={arenaLeaderboard}
        pagination={pagination}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
        onFetchAllForExport={handleFetchAllForExport}
      />
      {resultId && <ArtifactsList evaluationId={resultId} />}
    </div>
  );
}
