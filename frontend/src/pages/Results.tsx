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
    // Group results by evaluation_id and compute aggregates
    const resultsByEval = new Map<string, typeof results>();
    for (const r of results) {
      const existing = resultsByEval.get(r.evaluation_id) ?? [];
      existing.push(r);
      resultsByEval.set(r.evaluation_id, existing);
    }

    // Build rows from evaluations that have completed
    const completedEvals = evaluations.filter(
      (e) => e.status === 'completed' || e.status === 'failed',
    );

    return completedEvals.map((evaluation) => {
      const evalResults = resultsByEval.get(evaluation.id) ?? [];
      const scores = evalResults.filter((r) => r.score != null).map((r) => r.score!);
      const passedCount = evalResults.filter((r) => r.passed === true).length;
      const totalItems = evalResults.length;
      const meanScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
      const passRate = totalItems > 0 ? passedCount / totalItems : 0;

      return {
        evaluationId: evaluation.id,
        resultId: evaluation.id,
        name: evaluation.name,
        mode: evaluation.mode ?? 'qa',
        status: evaluation.status,
        totalItems,
        passRate,
        meanScore,
        createdAt: evaluation.created_at,
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
