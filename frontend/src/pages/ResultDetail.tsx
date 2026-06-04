import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { ResultDetailView } from '@/components/results';
import { api } from '@/services/api';
import type { DatasetItem, ArenaLeaderboardResponse } from '@/types';

export default function ResultDetail() {
  const { resultId } = useParams<{ resultId: string }>();
  const { results, isLoading, error, fetchResults } = useResultStore();
  const { evaluations, fetchEvaluations } = useEvaluationStore();
  const [datasetItems, setDatasetItems] = useState<DatasetItem[]>([]);
  const [arenaLeaderboard, setArenaLeaderboard] = useState<ArenaLeaderboardResponse | null>(null);

  useEffect(() => {
    if (resultId) {
      void fetchResults(resultId);
      void fetchEvaluations();
    }
  }, [resultId, fetchResults, fetchEvaluations]);

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

  const scores = results.filter((r) => r.score != null).map((r) => r.score!);
  const passedCount = results.filter((r) => r.passed === true).length;
  const failedCount = results.filter((r) => r.passed === false).length;
  const sorted = [...scores].sort((a, b) => a - b);
  const meanScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const medianScore = sorted.length > 0 ? (sorted[Math.floor(sorted.length / 2)] ?? 0) : 0;

  const aggregateMetrics = {
    total_items: results.length,
    passed_items: passedCount,
    failed_items: failedCount,
    mean_score: meanScore,
    median_score: medianScore,
    pass_rate: results.length > 0 ? passedCount / results.length : 0,
    score_distribution: {},
  };

  return (
    <ResultDetailView
      results={results}
      aggregateMetrics={aggregateMetrics}
      evaluationName={evaluation?.name}
      evaluationMode={evaluation?.mode}
      datasetItems={datasetItems}
      arenaLeaderboard={arenaLeaderboard}
    />
  );
}
