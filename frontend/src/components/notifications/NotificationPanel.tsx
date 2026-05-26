import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  Trash2,
} from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import {
  useNotificationStore,
  type Notification,
  type NotificationType,
} from '@/stores/notificationStore';

const typeConfig: Record<
  NotificationType,
  { icon: typeof CheckCircle; color: string; bgColor: string }
> = {
  success: {
    icon: CheckCircle,
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-950/30',
  },
  error: {
    icon: XCircle,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-50 dark:bg-yellow-950/30',
  },
  info: {
    icon: Info,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
  },
};

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return 'just now';
  if (diffMinutes < 60)
    return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
  if (diffHours < 24)
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
}

function NotificationCard({
  notification,
  onMarkAsRead,
  onRemove,
}: {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onRemove: (id: string) => void;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const config = typeConfig[notification.type];
  const Icon = config.icon;

  return (
    <div
      role="article"
      className={`relative rounded-md border p-3 transition-colors ${
        notification.read
          ? 'bg-background'
          : `border-l-4 border-l-primary/50 ${config.bgColor}`
      }`}
      onClick={() => {
        if (!notification.read) {
          onMarkAsRead(notification.id);
        }
      }}
    >
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${config.color}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium leading-tight">
              {notification.title}
            </p>
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-5 w-5 shrink-0 opacity-0 group-hover/card:opacity-100 hover:opacity-100 focus:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                onRemove(notification.id);
              }}
              aria-label="Remove notification"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {notification.message}
          </p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            {formatRelativeTime(notification.timestamp)}
          </p>

          {notification.details && (
            <div className="mt-2">
              <button
                type="button"
                className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                onClick={(e) => {
                  e.stopPropagation();
                  setDetailsOpen(!detailsOpen);
                }}
              >
                {detailsOpen ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
                Details
              </button>
              {detailsOpen && (
                <pre className="mt-1 max-h-40 overflow-auto rounded bg-muted p-2 text-xs whitespace-pre-wrap">
                  {notification.details}
                </pre>
              )}
            </div>
          )}

          {notification.evaluationId && (
            <Link
              to={`/results/${notification.evaluationId}`}
              className="mt-2 inline-block text-xs font-medium text-primary hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              View Results
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export function NotificationPanel() {
  const {
    notifications,
    isOpen,
    setOpen,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    unreadCount,
  } = useNotificationStore();

  return (
    <Sheet open={isOpen} onOpenChange={setOpen}>
      <SheetContent side="right" className="flex flex-col gap-0 p-0">
        <SheetHeader className="border-b px-4 py-3">
          <div className="flex items-center justify-between">
            <SheetTitle>Notifications</SheetTitle>
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={markAllAsRead}
                >
                  Mark all read
                </Button>
              )}
              {notifications.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-muted-foreground"
                  onClick={clearAll}
                >
                  Clear all
                </Button>
              )}
            </div>
          </div>
          <SheetDescription className="sr-only">
            View and manage your notifications
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Info className="mb-2 h-8 w-8 opacity-40" />
              <p className="text-sm">No notifications yet</p>
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {notifications.map((notification) => (
                <div key={notification.id} className="group/card">
                  <NotificationCard
                    notification={notification}
                    onMarkAsRead={markAsRead}
                    onRemove={removeNotification}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
