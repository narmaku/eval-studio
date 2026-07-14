import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Play, Database, BarChart3, MessageSquare, Settings } from 'lucide-react';

import { useAppVersion } from '@/hooks/useAppVersion';
import { cn } from '@/lib/utils';
import { useEvaluationStore } from '@/stores/evaluationStore';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  matchPaths?: string[];
}

const workspaceItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  {
    to: '/evaluate',
    label: 'Evaluate',
    icon: Play,
    matchPaths: ['/evaluate'],
  },
  { to: '/datasets', label: 'Datasets', icon: Database },
  {
    to: '/results',
    label: 'Results',
    icon: BarChart3,
    matchPaths: ['/results'],
  },
  {
    to: '/sessions',
    label: 'Sessions',
    icon: MessageSquare,
    matchPaths: ['/sessions'],
  },
];

const configItems: NavItem[] = [{ to: '/settings', label: 'Settings', icon: Settings }];

function isPathActive(pathname: string, item: NavItem): boolean {
  if (item.to === '/') return pathname === '/';
  if (item.matchPaths) {
    return item.matchPaths.some((p) => pathname.startsWith(p));
  }
  return pathname.startsWith(item.to);
}

function NavGroup({ label, items }: { label: string; items: NavItem[] }) {
  const location = useLocation();
  const getRunningEvaluation = useEvaluationStore((s) => s.getRunningEvaluation);
  useEvaluationStore((s) => s.currentEvaluation);
  const runningEval = getRunningEvaluation();

  return (
    <div className="mb-2">
      <div className="px-4 py-2">
        <span className="text-[10.5px] font-semibold tracking-[0.06em] uppercase text-text-3">
          {label}
        </span>
      </div>
      <div className="flex flex-col gap-0.5 px-2">
        {items.map((item) => {
          const active = isPathActive(location.pathname, item);
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={cn(
                'group relative flex h-[38px] items-center gap-2.5 rounded-[9px] px-3 text-[13px] transition-colors',
                active
                  ? 'bg-surface-3 font-[560] text-foreground'
                  : 'font-[470] text-text-2 hover:bg-surface-3',
              )}
            >
              {active && (
                <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r-full bg-accent" />
              )}
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
              {item.to === '/evaluate' && runningEval && (
                <span
                  className="ml-auto h-2 w-2 rounded-full bg-warn animate-es-pulse"
                  title={`Running: ${runningEval.name}`}
                />
              )}
            </NavLink>
          );
        })}
      </div>
    </div>
  );
}

export function Sidebar(): React.JSX.Element {
  const version = useAppVersion();

  return (
    <aside className="flex h-screen w-[var(--sidebar-width)] shrink-0 flex-col border-r border-border bg-surface-2">
      {/* Brand block */}
      <div className="flex h-[var(--topbar-height)] shrink-0 items-center gap-2.5 border-b border-border px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <span className="text-sm font-bold">&lt;/&gt;</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold leading-tight">eval-studio</span>
          <span className="font-mono text-[10.5px] text-text-3">v{version}</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3">
        <NavGroup label="Workspace" items={workspaceItems} />
        <NavGroup label="Configure" items={configItems} />
      </nav>

      {/* User footer */}
      <div className="shrink-0 border-t border-border px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-2 text-xs font-semibold text-white">
            SM
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium leading-tight">SME · local</span>
            <span className="font-mono text-[10.5px] text-text-3">trusted domain</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
