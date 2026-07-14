import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
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
        config: evaluation.config,
        metadata: evaluation.metadata,
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
      {/* Header */}
      <div>
        <h1 className="text-[25px] font-semibold tracking-[-0.02em]">Results</h1>
        <p className="text-[13px] text-text-2">
          Browse historical runs, compare evaluations, and export data for analysis.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <p className="text-[13px] text-text-3">Loading results...</p>
        </div>
      )}

      {error && !isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <p className="text-[13px] font-medium text-fail">Error loading results</p>
            <p className="text-[12px] text-text-3">{error}</p>
          </div>
        </div>
      )}

      {!isLoading && !error && <EvaluationResultsList rows={rows} />}

      {selectedEvaluationIds.length > 0 && (
        <div
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2"
          data-testid="compare-action-bar"
        >
          <div className="flex items-center gap-4 rounded-[13px] border border-border bg-card px-6 py-3 shadow">
            <span className="text-[12.5px] text-text-2">
              {selectedEvaluationIds.length} evaluation
              {selectedEvaluationIds.length !== 1 ? 's' : ''} selected
            </span>
            <button
              className="rounded-[9px] border border-border px-3 py-1.5 text-[12px] font-medium text-text-2 transition-colors hover:bg-surface-3"
              onClick={clearSelection}
            >
              Clear
            </button>
            <button
              className="rounded-[9px] bg-primary px-3 py-1.5 text-[12px] font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
              disabled={!canCompare}
              onClick={handleCompare}
            >
              Compare
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
