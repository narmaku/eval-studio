import { useEffect, useState } from 'react';
import { api } from '@/services/api';
import { EvaluatorDetail } from './EvaluatorDetail';
import { cn } from '@/lib/utils';
import { getModeBadgeClasses, getModeLabel } from '@/lib/designUtils';
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
        <p className="text-[13px] text-text-3">Loading evaluators...</p>
      </div>
    );
  }

  if (error) {
    return <div className="rounded-[14px] bg-fail-bg p-4 text-[13px] text-fail">{error}</div>;
  }

  if (evaluators.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-[14px] border border-dashed border-border py-12">
        <p className="text-[13px] text-text-3">
          No evaluators configured. Add evaluator definitions to config/evaluators.yaml
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {evaluators.map((evaluator) => (
          <div
            key={evaluator.id}
            className="flex flex-col rounded-[14px] border border-border bg-card p-5 shadow-sm transition-all hover:shadow"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-[14px] font-semibold">{evaluator.name}</h3>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {evaluator.builtin && (
                  <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                    Built-in
                  </span>
                )}
                <StatusIndicator available={evaluator.available} />
              </div>
            </div>

            <div className="mt-2 space-y-2">
              <p className="text-[12px] text-text-2 line-clamp-2">{evaluator.description}</p>
              <div className="flex flex-wrap gap-1">
                {evaluator.modes.map((mode) => (
                  <span
                    key={mode}
                    className={cn(
                      'rounded-[6px] px-2 py-0.5 text-[10px] font-semibold uppercase',
                      getModeBadgeClasses(mode),
                    )}
                  >
                    {getModeLabel(mode)}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-auto pt-3">
              <button
                className="w-full rounded-[9px] border border-border px-3 py-1.5 text-[12px] font-medium text-text-2 transition-colors hover:bg-surface-3"
                onClick={() => handleConfigure(evaluator)}
              >
                Configure
              </button>
            </div>
          </div>
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
    <span className="flex items-center gap-1 text-[11px] text-text-2">
      <span
        className={cn('inline-block h-2 w-2 rounded-full', available ? 'bg-pass' : 'bg-fail')}
      />
      {available ? 'Available' : 'Unavailable'}
    </span>
  );
}
