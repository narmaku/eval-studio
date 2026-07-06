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
      <div className="grid grid-cols-2 gap-4">
        {modes.map((mode) => {
          const Icon = mode.icon;
          return (
            <Link key={mode.to} to={mode.to} className="group">
              <div
                className={cn(
                  'relative flex flex-col rounded-[15px] border border-border bg-card p-6 shadow-sm',
                  'transition-all duration-150 hover:-translate-y-0.5 hover:border-accent hover:shadow',
                )}
              >
                <div className="flex items-start justify-between mb-4">
                  <div
                    className={cn(
                      'flex h-[42px] w-[42px] items-center justify-center rounded-xl',
                      mode.colorClasses,
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <span
                    className={cn(
                      'rounded-[6px] px-2.5 py-1 text-[10px] font-semibold tracking-[0.05em] uppercase',
                      mode.tagClasses,
                    )}
                  >
                    {mode.tag}
                  </span>
                </div>
                <h3 className="text-[17px] font-semibold mb-1.5">{mode.title}</h3>
                <p className="text-[12.5px] text-text-2 mb-4 flex-1">{mode.description}</p>
                <span className="flex items-center gap-1 text-[12px] font-medium text-accent">
                  Configure <ArrowRight className="h-3 w-3" />
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
