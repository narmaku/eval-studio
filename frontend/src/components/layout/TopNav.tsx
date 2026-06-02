import { NavLink } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNotificationStore } from '@/stores/notificationStore';
import { useEvaluationStore } from '@/stores/evaluationStore';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/evaluate', label: 'Evaluate' },
  { to: '/datasets', label: 'Datasets' },
  { to: '/results', label: 'Results' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/environments', label: 'Environments' },
];

export function TopNav() {
  const { unreadCount, toggleOpen } = useNotificationStore();
  const getRunningEvaluation = useEvaluationStore((state) => state.getRunningEvaluation);
  // Subscribe to currentEvaluation to trigger re-renders when running state changes
  const _currentEvaluation = useEvaluationStore((state) => state.currentEvaluation);

  // Read from sessionStorage
  const runningEvaluation = getRunningEvaluation();

  return (
    <header className="border-b bg-background">
      <div className="flex h-14 items-center px-6">
        <span className="text-lg font-semibold mr-8">eval-studio</span>
        <nav className="flex items-center gap-6">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors hover:text-primary ${
                  isActive ? 'text-foreground' : 'text-muted-foreground'
                }`
              }
            >
              <span className="flex items-center gap-1.5">
                {item.label}
                {item.to === '/evaluate' && runningEvaluation && (
                  <span
                    className="relative flex h-2 w-2"
                    title={`Running: ${runningEvaluation.name}`}
                  >
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                  </span>
                )}
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon-sm"
            className="relative"
            onClick={toggleOpen}
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span
                className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-destructive-foreground"
                data-testid="notification-badge"
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </Button>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `text-sm font-medium transition-colors hover:text-primary ${
                isActive ? 'text-foreground' : 'text-muted-foreground'
              }`
            }
          >
            Settings
          </NavLink>
        </div>
      </div>
    </header>
  );
}
