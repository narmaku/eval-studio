import { useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Bell, Search, Sun, Moon, BarChart3, MessageSquare, Database } from 'lucide-react';
import { useNotificationStore } from '@/stores/notificationStore';
import { useSearchStore, type SearchResult } from '@/stores/searchStore';
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
  '/search': 'results',
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

const typeIcons: Record<SearchResult['type'], React.ComponentType<{ className?: string }>> = {
  evaluation: BarChart3,
  session: MessageSquare,
  dataset: Database,
};

export function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { unreadCount, toggleOpen } = useNotificationStore();
  const { query, isOpen, results, setQuery, setOpen, search, clear } = useSearchStore();
  const { theme, toggleTheme } = useTheme();
  const { root, leaf } = getBreadcrumb(location.pathname);
  const blurTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    search(value);
  };

  const handleFocus = () => {
    if (blurTimeoutRef.current) {
      clearTimeout(blurTimeoutRef.current);
      blurTimeoutRef.current = null;
    }
    setOpen(true);
  };

  const handleBlur = () => {
    blurTimeoutRef.current = setTimeout(() => {
      setOpen(false);
    }, 200);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
      clear();
    }
    if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  const handleResultClick = (result: SearchResult) => {
    navigate(result.path);
    clear();
  };

  const showDropdown = isOpen && query.trim().length > 0;

  return (
    <header className="flex h-[var(--topbar-height)] shrink-0 items-center gap-4 border-b border-border bg-background/80 px-7 backdrop-blur-md">
      {/* Breadcrumb */}
      <div className="font-mono text-[12.5px]">
        <span className="text-text-3">{root}</span>
        <span className="text-text-3"> / </span>
        <span className="text-text-2">{leaf}</span>
      </div>

      <div className="flex-1" />

      {/* Search */}
      <div className="relative">
        <div className="flex h-8 w-[240px] items-center gap-2 rounded-[9px] border border-border bg-transparent px-2.5 focus-within:border-accent">
          <Search className="h-3.5 w-3.5 shrink-0 text-text-3" />
          <input
            type="text"
            value={query}
            onChange={handleSearchChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            placeholder="Search..."
            className="h-full w-full bg-transparent text-[12px] text-foreground placeholder:text-text-3 focus:outline-none"
          />
        </div>

        {showDropdown && (
          <div className="absolute top-full right-0 z-50 mt-1 w-[360px] overflow-hidden rounded-[12px] border border-border bg-card shadow-lg">
            {results.length > 0 ? (
              <>
                {results.map((result) => {
                  const Icon = typeIcons[result.type];
                  return (
                    <button
                      key={`${result.type}-${result.id}`}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => handleResultClick(result)}
                      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-surface-3"
                    >
                      <Icon className="h-4 w-4 shrink-0 text-text-3" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[13px] font-medium text-foreground">
                          {result.name}
                        </div>
                        <div className="truncate text-[11px] text-text-3">{result.subtitle}</div>
                      </div>
                    </button>
                  );
                })}
                <div className="border-t border-border px-3 py-2 text-[11px] text-text-3">
                  Press Enter to see all results
                </div>
              </>
            ) : (
              <div className="px-3 py-4 text-center text-[12px] text-text-3">
                No results for &lsquo;{query}&rsquo;
              </div>
            )}
          </div>
        )}
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
