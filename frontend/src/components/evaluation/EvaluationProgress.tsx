import { useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EvaluationLogPanel } from './EvaluationLogPanel';
import { useEvaluationStore } from '@/stores/evaluationStore';
import type { EvaluationStatus } from '@/types';

interface EvaluationProgressProps {
  evaluationId: string;
  onComplete: () => void;
}

const statusVariant: Record<EvaluationStatus, 'outline' | 'default' | 'secondary' | 'destructive'> =
  {
    pending: 'outline',
    running: 'default',
    completed: 'secondary',
    failed: 'destructive',
    cancelled: 'outline',
  };

const statusLabel: Record<EvaluationStatus, string> = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

export function EvaluationProgress({ evaluationId, onComplete }: EvaluationProgressProps) {
  const currentEvaluation = useEvaluationStore((state) => state.currentEvaluation);
  const progress = useEvaluationStore((state) => state.progress);
  const connectToEvaluation = useEvaluationStore((state) => state.connectToEvaluation);
  const disconnectFromEvaluation = useEvaluationStore((state) => state.disconnectFromEvaluation);

  useEffect(() => {
    connectToEvaluation(evaluationId);
    return () => {
      disconnectFromEvaluation();
    };
  }, [evaluationId, connectToEvaluation, disconnectFromEvaluation]);

  // Trigger onComplete when evaluation finishes
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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          Evaluation Progress
          <Badge variant={statusVariant[status]}>{statusLabel[status]}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Progress bar */}
        {(status === 'running' || status === 'pending') && (
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            {hasProgress ? (
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            ) : (
              <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
            )}
          </div>
        )}

        {/* Progress text */}
        {status === 'running' && hasProgress && (
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium">{progress.completed} / {progress.total}</span>
              {progress.currentItem && (
                <span className="ml-2">— {progress.currentItem}</span>
              )}
            </p>
            {progress.contestantModel && (
              <p className="text-xs text-muted-foreground">
                Model: <span className="font-medium">{progress.contestantModel}</span>
              </p>
            )}
          </div>
        )}

        {status === 'running' && !hasProgress && (
          <p className="text-sm text-muted-foreground">Scoring items...</p>
        )}

        {status === 'pending' && (
          <p className="text-sm text-muted-foreground">Waiting for evaluation to start...</p>
        )}

        {status === 'completed' && (
          <p className="text-sm text-muted-foreground">Evaluation completed successfully.</p>
        )}

        {status === 'failed' && (
          <div className="space-y-1">
            <p className="text-sm text-destructive">Evaluation failed.</p>
          </div>
        )}

        {/* Log Panel */}
        {(status === 'running' || status === 'pending') && <EvaluationLogPanel />}
      </CardContent>
    </Card>
  );
}
