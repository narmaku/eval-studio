import { useLocation } from 'react-router-dom';
import { Bell, Search, Sun, Moon } from 'lucide-react';
import { useNotificationStore } from '@/stores/notificationStore';
import { useTheme } from '@/hooks/useTheme';

const routeLabels: Record<string, string> = {
  '/': 'dashboard',
  '/evaluate': 'select mode',
  '/evaluate/qa': 'qa · setup',
  '/evaluate/rag': 'rag · setup',
  '/evaluate/agent': 'agent · setup',
  '/evaluate/arena': 'arena · setup',
  '/datasets': 'library',
  '/results': 'all runs',
  '/results/compare': 'compare',
  '/sessions': 'all',
  '/settings': 'providers',
};

function getBreadcrumb(pathname: string): { root: string; leaf: string } {
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0) return { root: 'workspace', leaf: 'dashboard' };

  const root = segments[0] ?? 'workspace';

  if (routeLabels[pathname]) {
    return { root, leaf: routeLabels[pathname] };
  }

  if (segments.length >= 2) {
    if (root === 'results') return { root, leaf: 'run detail' };
    if (root === 'sessions') return { root, leaf: 'transcript' };
    if (root === 'evaluate') return { root, leaf: segments[1] ?? 'setup' };
  }

  return { root, leaf: routeLabels[`/${root}`] ?? root };
}

export function TopBar() {
  const location = useLocation();
  const { unreadCount, toggleOpen } = useNotificationStore();
  const { theme, toggleTheme } = useTheme();
  const { root, leaf } = getBreadcrumb(location.pathname);

  return (
    <header className="flex h-[var(--topbar-height)] shrink-0 items-center gap-4 border-b border-border bg-background/80 px-7 backdrop-blur-md">
      {/* Breadcrumb */}
      <div className="font-mono text-[12.5px]">
        <span className="text-text-3">{root}</span>
        <span className="text-text-3"> / </span>
        <span className="text-text-2">{leaf}</span>
      </div>

      <div className="flex-1" />

      {/* Search affordance (visual only) */}
      <div className="flex h-8 w-[200px] items-center gap-2 rounded-[9px] border border-border px-2.5">
        <Search className="h-3.5 w-3.5 text-text-3" />
        <span className="flex-1 text-[12px] text-text-3">Search evaluations...</span>
        <kbd className="rounded border border-border-strong bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-3">
          ⌘K
        </kbd>
      </div>

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="flex h-[34px] w-[34px] items-center justify-center rounded-[9px] text-text-2 transition-colors hover:bg-surface-3"
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      {/* Notifications */}
      <button
        onClick={toggleOpen}
        className="relative flex h-[34px] w-[34px] items-center justify-center rounded-[9px] text-text-2 transition-colors hover:bg-surface-3"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-fail px-1 text-[10px] font-medium text-white">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
    </header>
  );
}
