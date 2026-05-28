import { useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useEvaluatorStore } from '@/stores/evaluatorStore';

interface EvaluatorSelectorProps {
  mode: string;
  onSelect?: (evaluatorId: string) => void;
}

export function EvaluatorSelector({ mode, onSelect }: EvaluatorSelectorProps) {
  const { evaluators, selectedEvaluatorId, isLoading, error, fetchEvaluators, selectEvaluator } =
    useEvaluatorStore();

  useEffect(() => {
    void fetchEvaluators(mode);
  }, [mode, fetchEvaluators]);

  const handleSelect = (evaluatorId: string) => {
    selectEvaluator(evaluatorId);
    onSelect?.(evaluatorId);
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        <h2 className="text-sm font-medium">Evaluator</h2>
        <p className="text-sm text-muted-foreground">Loading evaluators...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-2">
        <h2 className="text-sm font-medium">Evaluator</h2>
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" size="sm" onClick={() => void fetchEvaluators(mode)}>
          Retry
        </Button>
      </div>
    );
  }

  if (evaluators.length === 0) {
    return (
      <div className="space-y-2">
        <h2 className="text-sm font-medium">Evaluator</h2>
        <p className="text-sm text-muted-foreground">No evaluators configured for this mode</p>
        <a href="/settings" className="text-sm text-primary underline">
          Configure in Settings
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h2 className="text-sm font-medium">Evaluator</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {evaluators.map((evaluator) => {
          const isSelected = selectedEvaluatorId === evaluator.id;
          return (
            <Card
              key={evaluator.id}
              className={`cursor-pointer transition-all ${
                isSelected ? 'ring-2 ring-primary' : ''
              } ${!evaluator.available ? 'opacity-50' : ''}`}
              onClick={() => handleSelect(evaluator.id)}
            >
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {evaluator.name}
                  {evaluator.builtin && (
                    <Badge variant="secondary" className="text-xs">
                      Built-in
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>{evaluator.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1">
                  {evaluator.modes.map((m) => (
                    <Badge key={m} variant="outline" className="text-xs">
                      {m}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
