import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { api } from '@/services/api';
import { EvaluatorDetail } from './EvaluatorDetail';
import type { EvaluatorInfo } from '@/types';

export function EvaluatorList() {
  const [evaluators, setEvaluators] = useState<EvaluatorInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvaluator, setSelectedEvaluator] = useState<EvaluatorInfo | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

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

  const handleConfigure = (evaluator: EvaluatorInfo) => {
    setSelectedEvaluator(evaluator);
    setDetailOpen(true);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <p className="text-sm text-muted-foreground">Loading evaluators...</p>
      </div>
    );
  }

  if (error) {
    return <div className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">{error}</div>;
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {evaluators.map((evaluator) => (
          <Card key={evaluator.id} className="flex flex-col">
            <CardContent className="flex flex-col gap-2 py-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <h3 className="font-medium truncate">{evaluator.name}</h3>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {evaluator.builtin && (
                    <Badge variant="outline" className="text-xs">
                      Built-in
                    </Badge>
                  )}
                  <StatusIndicator available={evaluator.available} />
                </div>
              </div>

              <div className="space-y-1">
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {evaluator.description}
                </p>
                <div className="flex flex-wrap gap-1">
                  {evaluator.modes.map((mode) => (
                    <Badge key={mode} variant="secondary" className="text-xs">
                      {mode}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="mt-auto pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => handleConfigure(evaluator)}
                >
                  Configure
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {selectedEvaluator && (
        <EvaluatorDetail
          open={detailOpen}
          onOpenChange={setDetailOpen}
          evaluator={selectedEvaluator}
        />
      )}
    </div>
  );
}

function StatusIndicator({ available }: { available: boolean }) {
  return (
    <span className="flex items-center gap-1 text-xs">
      <span
        className={`inline-block h-2 w-2 rounded-full ${available ? 'bg-green-500' : 'bg-red-500'}`}
      />
      {available ? 'Available' : 'Unavailable'}
    </span>
  );
}
