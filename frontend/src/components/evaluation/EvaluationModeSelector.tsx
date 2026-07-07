import { Link } from 'react-router-dom';
import { MessageSquare, BarChart3, Database, Trophy, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const modes = [
  {
    to: '/evaluate/qa',
    title: 'Q & A',
    tag: 'SINGLE-TURN',
    description:
      'Evaluate question-answer pairs with configurable LLM judges, rubrics, and pass thresholds.',
    icon: MessageSquare,
    colorClasses: 'bg-mode-qa-bg text-mode-qa-fg',
    tagClasses: 'bg-mode-qa-bg text-mode-qa-fg',
  },
  {
    to: '/evaluate/agent',
    title: 'Agent Chat',
    tag: 'MULTI-TURN',
    description:
      'Interactive or simulated multi-turn conversations with full tool-call tracing and scoring.',
    icon: BarChart3,
    colorClasses: 'bg-mode-agent-bg text-mode-agent-fg',
    tagClasses: 'bg-mode-agent-bg text-mode-agent-fg',
  },
  {
    to: '/evaluate/rag',
    title: 'RAG Pipeline',
    tag: 'RETRIEVAL',
    description:
      'Evaluate retrieval-augmented generation with chunk-level analysis and relevance metrics.',
    icon: Database,
    colorClasses: 'bg-mode-rag-bg text-mode-rag-fg',
    tagClasses: 'bg-mode-rag-bg text-mode-rag-fg',
  },
  {
    to: '/evaluate/arena',
    title: 'Model Arena',
    tag: 'COMPARE',
    description:
      'Run the same evaluation across multiple models side-by-side and rank by performance.',
    icon: Trophy,
    colorClasses: 'bg-mode-arena-bg text-mode-arena-fg',
    tagClasses: 'bg-mode-arena-bg text-mode-arena-fg',
  },
];

export function EvaluationModeSelector() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[25px] font-semibold tracking-[-0.02em]">Start new evaluation</h1>
        <p className="text-[13px] text-text-2">
          Pick a mode — the workspace adapts its setup and metrics to what you're testing.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3">
        {modes.map((mode) => {
          const Icon = mode.icon;
          return (
            <Link key={mode.to} to={mode.to} className="group">
              <div
                className={cn(
                  'relative flex items-center gap-4 rounded-[14px] border border-border bg-card px-5 py-4 shadow-sm',
                  'transition-all duration-150 hover:border-accent hover:shadow',
                )}
              >
                <div
                  className={cn(
                    'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
                    mode.colorClasses,
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-[15px] font-semibold">{mode.title}</h3>
                    <span
                      className={cn(
                        'rounded-[5px] px-2 py-0.5 text-[9px] font-semibold tracking-[0.05em] uppercase',
                        mode.tagClasses,
                      )}
                    >
                      {mode.tag}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[12px] text-text-2 line-clamp-1">{mode.description}</p>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-text-3 transition-colors group-hover:text-accent" />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
