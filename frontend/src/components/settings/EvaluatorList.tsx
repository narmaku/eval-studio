import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { api } from '@/services/api';
import type { EvaluatorInfo } from '@/types';

export function EvaluatorList() {
  const [evaluators, setEvaluators] = useState<EvaluatorInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchEvaluators = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.listEvaluators();
        setEvaluators(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch evaluators';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchEvaluators();
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <p className="text-sm text-muted-foreground">Loading evaluators...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
    );
  }

  if (evaluators.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12">
        <p className="text-sm text-muted-foreground">
          No evaluators configured. Add evaluator definitions to config/evaluators.yaml
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {evaluators.map((evaluator) => (
        <Card key={evaluator.id}>
          <CardContent className="py-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{evaluator.name}</h3>
                  {evaluator.builtin && <Badge variant="outline">Built-in</Badge>}
                  <StatusIndicator available={evaluator.available} />
                </div>
                <p className="text-xs text-muted-foreground">{evaluator.description}</p>
                <div className="flex gap-1 pt-1">
                  {evaluator.modes.map((mode) => (
                    <Badge key={mode} variant="secondary" className="text-xs">
                      {mode}
                    </Badge>
                  ))}
                </div>
                {Object.keys(evaluator.defaults).length > 0 && (
                  <p className="text-xs text-muted-foreground pt-1">
                    Defaults:{' '}
                    {Object.entries(evaluator.defaults)
                      .map(([k, v]) => `${k}=${String(v)}`)
                      .join(', ')}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function StatusIndicator({ available }: { available: boolean }) {
  return (
    <span className="flex items-center gap-1 text-xs">
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          available ? 'bg-green-500' : 'bg-red-500'
        }`}
      />
      {available ? 'Available' : 'Unavailable'}
    </span>
  );
}
