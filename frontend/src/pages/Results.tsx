import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { EvaluationResultsList } from '@/components/results';
import type { EvaluationResultRow } from '@/components/results';

export default function Results() {
  const navigate = useNavigate();
  const { selectedEvaluationIds, referenceEvaluationId, clearSelection } = useResultStore();

  const {
    evaluations,
    isLoading: evaluationsLoading,
    error: evaluationsError,
    fetchEvaluations,
  } = useEvaluationStore();

  useEffect(() => {
    void fetchEvaluations();
  }, [fetchEvaluations]);

  const isLoading = evaluationsLoading;
  const error = evaluationsError;

  const rows = useMemo<EvaluationResultRow[]>(() => {
    // Build rows from evaluations that have completed, using server-side aggregates
    const completedEvals = evaluations.filter(
      (e) => e.status === 'completed' || e.status === 'failed',
    );

    return completedEvals.map((evaluation) => {
      return {
        evaluationId: evaluation.id,
        resultId: evaluation.id,
        name: evaluation.name,
        mode: evaluation.mode ?? 'qa',
        status: evaluation.status,
        totalItems: evaluation.result_count ?? 0,
        passRate: evaluation.pass_rate ?? 0,
        meanScore: evaluation.average_score ?? 0,
        createdAt: evaluation.created_at,
        datasetId: evaluation.dataset_id,
      };
    });
  }, [evaluations]);

  const canCompare = selectedEvaluationIds.length >= 2;

  const handleCompare = () => {
    const params = new URLSearchParams();
    selectedEvaluationIds.forEach((id) => params.append('ids', id));
    if (referenceEvaluationId) {
      params.set('ref', referenceEvaluationId);
    }
    navigate(`/results/compare?${params.toString()}`);
  };

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

      {selectedEvaluationIds.length > 0 && (
        <div
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2"
          data-testid="compare-action-bar"
        >
          <div className="flex items-center gap-4 rounded-lg border bg-background px-6 py-3 shadow-lg">
            <span className="text-sm text-muted-foreground">
              {selectedEvaluationIds.length} evaluation
              {selectedEvaluationIds.length !== 1 ? 's' : ''} selected
            </span>
            <Button variant="outline" size="sm" onClick={clearSelection}>
              Clear Selection
            </Button>
            <Button size="sm" disabled={!canCompare} onClick={handleCompare}>
              Compare
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
