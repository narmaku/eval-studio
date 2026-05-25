import { useEffect, useMemo } from 'react';
import { Separator } from '@/components/ui/separator';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { EvaluationResultsList } from '@/components/results';
import type { EvaluationResultRow } from '@/components/results';

export default function Results() {
  const {
    results,
    isLoading: resultsLoading,
    error: resultsError,
    fetchResults,
  } = useResultStore();

  const {
    evaluations,
    isLoading: evaluationsLoading,
    error: evaluationsError,
    fetchEvaluations,
  } = useEvaluationStore();

  useEffect(() => {
    void fetchEvaluations();
    void fetchResults();
  }, [fetchEvaluations, fetchResults]);

  const isLoading = resultsLoading || evaluationsLoading;
  const error = resultsError ?? evaluationsError;

  const rows = useMemo<EvaluationResultRow[]>(() => {
    const evaluationMap = new Map(evaluations.map((e) => [e.id, e]));

    return results.map((result) => {
      const evaluation = evaluationMap.get(result.evaluation_id);
      return {
        evaluationId: result.evaluation_id,
        resultId: result.id,
        name: evaluation?.name ?? 'Unknown Evaluation',
        mode: evaluation?.mode ?? 'qa',
        status: evaluation?.status ?? result.status,
        totalItems: result.aggregate_metrics.total_items,
        passRate: result.aggregate_metrics.pass_rate,
        meanScore: result.aggregate_metrics.mean_score,
        createdAt: result.created_at,
      };
    });
  }, [results, evaluations]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Results</h1>
        <p className="text-muted-foreground">
          Browse historical evaluation results, compare runs, and export data for further analysis.
        </p>
      </div>
      <Separator />

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading results...</p>
        </div>
      )}

      {error && !isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <p className="text-destructive font-medium">Error loading results</p>
            <p className="text-muted-foreground text-sm">{error}</p>
          </div>
        </div>
      )}

      {!isLoading && !error && <EvaluationResultsList rows={rows} />}
    </div>
  );
}
