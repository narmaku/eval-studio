import { useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
  const { currentEvaluation, pollEvaluation } = useEvaluationStore();

  useEffect(() => {
    const cleanup = pollEvaluation(evaluationId, onComplete);
    return cleanup;
  }, [evaluationId, onComplete, pollEvaluation]);

  const status = currentEvaluation?.status ?? 'pending';

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          Evaluation Progress
          <Badge variant={statusVariant[status]}>{statusLabel[status]}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Indeterminate progress bar for running/pending states */}
        {(status === 'running' || status === 'pending') && (
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
          </div>
        )}

        {status === 'running' && <p className="text-sm text-muted-foreground">Scoring items...</p>}

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
      </CardContent>
    </Card>
  );
}
