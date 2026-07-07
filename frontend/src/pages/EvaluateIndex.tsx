import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { EvaluationModeSelector } from '@/components/evaluation/EvaluationModeSelector';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { getModeBadgeClasses, getModeLabel } from '@/lib/designUtils';
import { cn } from '@/lib/utils';

const modeRoutes: Record<string, string> = {
  qa: '/evaluate/qa',
  agent: '/evaluate/agent',
  rag: '/evaluate/rag',
  arena: '/evaluate/arena',
};

function ActiveEvaluationPanel() {
  const runningEval = useEvaluationStore((s) => s.getRunningEvaluation)();
  useEvaluationStore((s) => s.currentEvaluation);
  const progress = useEvaluationStore((s) => s.progress);

  if (!runningEval) {
    return (
      <div className="flex flex-col items-center justify-center rounded-[14px] border border-dashed border-border bg-surface-2 px-6 py-12 text-center">
        <p className="text-[13px] text-text-3">No active evaluations</p>
        <p className="mt-1 text-[11px] text-text-3">
          Pick a mode and start an evaluation to see it here.
        </p>
      </div>
    );
  }

  const route = modeRoutes[runningEval.mode] ?? '/evaluate';
  const hasProgress = progress && progress.total > 0;
  const progressPercent = hasProgress ? (progress.completed / progress.total) * 100 : 0;

  return (
    <div className="space-y-3">
      <Link to={route} className="group block">
        <div className="rounded-[14px] border border-warn/40 bg-card p-5 shadow-sm transition-all hover:shadow">
          {/* Mode + Status */}
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'rounded-[6px] px-2.5 py-1 text-[10px] font-semibold tracking-[0.05em] uppercase',
                getModeBadgeClasses(runningEval.mode),
              )}
            >
              {getModeLabel(runningEval.mode)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-warn-bg px-2.5 py-1 text-[10px] font-semibold text-warn">
              <Loader2 className="h-3 w-3 animate-spin" />
              Running
            </span>
          </div>

          {/* Name */}
          <h3 className="mt-3 truncate text-[15px] font-semibold text-foreground">
            {runningEval.name}
          </h3>

          {/* Progress bar */}
          {hasProgress && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-mono font-medium text-text-2">
                  {progress.completed} / {progress.total}
                </span>
                <span className="text-text-3">{Math.round(progressPercent)}%</span>
              </div>
              <div className="mt-1.5 h-[6px] overflow-hidden rounded-full bg-surface-3">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${progressPercent}%`,
                    background: 'linear-gradient(90deg, var(--accent), var(--accent-2))',
                  }}
                />
              </div>
              {progress.currentItem && (
                <p className="mt-1.5 truncate text-[11px] text-text-3">{progress.currentItem}</p>
              )}
            </div>
          )}

          {!hasProgress && (
            <div className="mt-3 h-[6px] overflow-hidden rounded-full bg-surface-3">
              <div
                className="h-full w-1/3 rounded-full"
                style={{
                  background: 'linear-gradient(90deg, var(--accent), var(--accent-2))',
                  animation: 'es-indet 1.5s ease-in-out infinite',
                }}
              />
            </div>
          )}

          <p className="mt-3 text-[11px] text-accent group-hover:underline">
            View live progress &rarr;
          </p>
        </div>
      </Link>
    </div>
  );
}

export default function EvaluateIndex() {
  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_340px]">
      {/* Left: mode selector */}
      <EvaluationModeSelector />

      {/* Right: active evaluations */}
      <div>
        <h2 className="mb-3 text-[10.5px] font-semibold tracking-[0.06em] uppercase text-text-3">
          Active evaluations
        </h2>
        <ActiveEvaluationPanel />
      </div>
    </div>
  );
}
