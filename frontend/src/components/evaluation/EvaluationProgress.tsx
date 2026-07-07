import { useEffect } from 'react';
import { EvaluationLogPanel } from './EvaluationLogPanel';
import { useEvaluationStore } from '@/stores/evaluationStore';

interface EvaluationProgressProps {
  evaluationId: string;
  onComplete: () => void;
}

export function EvaluationProgress({ evaluationId, onComplete }: EvaluationProgressProps) {
  const currentEvaluation = useEvaluationStore((state) => state.currentEvaluation);
  const progress = useEvaluationStore((state) => state.progress);
  const connectToEvaluation = useEvaluationStore((state) => state.connectToEvaluation);

  useEffect(() => {
    connectToEvaluation(evaluationId);
  }, [evaluationId, connectToEvaluation]);

  useEffect(() => {
    if (
      currentEvaluation?.status === 'completed' ||
      currentEvaluation?.status === 'failed' ||
      currentEvaluation?.status === 'cancelled'
    ) {
      onComplete();
    }
  }, [currentEvaluation?.status, onComplete]);

  const status = currentEvaluation?.status ?? 'pending';
  const progressPercent =
    progress && progress.total > 0 ? (progress.completed / progress.total) * 100 : 0;
  const hasProgress = progress !== null && progress.total > 0;

  return (
    <div className="space-y-4">
      {/* Title + status pill */}
      <div className="flex items-center gap-3">
        <h2 className="text-[19px] font-semibold">{currentEvaluation?.name ?? 'Evaluation'}</h2>
        {status === 'running' && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-warn-bg px-3 py-1 text-[11px] font-semibold text-warn">
            <span className="h-1.5 w-1.5 rounded-full bg-warn animate-es-pulse" />
            Running
          </span>
        )}
        {status === 'pending' && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-3 px-3 py-1 text-[11px] font-semibold text-text-2">
            Pending
          </span>
        )}
      </div>

      {status === 'running' && (
        <p className="text-[13px] text-text-2">
          Live logs streamed over WebSocket
          {progress?.contestantModel && ` — scoring against ${progress.contestantModel}`}
        </p>
      )}

      {/* Progress card */}
      <div className="rounded-[14px] border border-border bg-card shadow-sm overflow-hidden">
        {/* Header with progress count */}
        {hasProgress && (
          <div className="flex items-center justify-between px-5 pt-4 pb-2">
            <span className="font-mono text-[13px] font-semibold">
              {progress.completed} / {progress.total} items
            </span>
            {progress.currentItem && (
              <span className="text-[12px] text-text-2 truncate max-w-[50%]">
                {progress.currentItem}
              </span>
            )}
          </div>
        )}

        {/* Progress bar */}
        {(status === 'running' || status === 'pending') && (
          <div className="mx-5 mb-3 h-[7px] overflow-hidden rounded-full bg-surface-3">
            {hasProgress ? (
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${progressPercent}%`,
                  background: 'linear-gradient(90deg, var(--accent), var(--accent-2))',
                }}
              />
            ) : (
              <div
                className="h-full w-1/3 rounded-full"
                style={{
                  background: 'linear-gradient(90deg, var(--accent), var(--accent-2))',
                  animation: 'es-indet 1.5s ease-in-out infinite',
                }}
              />
            )}
          </div>
        )}

        {/* Log panel */}
        <EvaluationLogPanel />
      </div>

      {/* Status messages for terminal states */}
      {status === 'completed' && (
        <p className="text-[13px] text-pass font-medium">Evaluation completed successfully.</p>
      )}
      {status === 'failed' && (
        <p className="text-[13px] text-fail font-medium">Evaluation failed.</p>
      )}
    </div>
  );
}
