import { create } from 'zustand';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  details?: string;
  timestamp: Date;
  read: boolean;
  evaluationId?: string;
}

const MAX_NOTIFICATIONS = 50;

interface NotificationStore {
  notifications: Notification[];
  unreadCount: number;
  isOpen: boolean;

  addNotification: (
    notification: Omit<Notification, 'id' | 'timestamp' | 'read'>,
  ) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  setOpen: (open: boolean) => void;
  toggleOpen: () => void;
}

function computeUnreadCount(notifications: Notification[]): number {
  return notifications.filter((n) => !n.read).length;
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  unreadCount: 0,
  isOpen: false,

  addNotification: (partial) => {
    const notification: Notification = {
      ...partial,
      id: crypto.randomUUID(),
      timestamp: new Date(),
      read: false,
    };
    set((state) => {
      const updated = [notification, ...state.notifications].slice(
        0,
        MAX_NOTIFICATIONS,
      );
      return { notifications: updated, unreadCount: computeUnreadCount(updated) };
    });
  },

  markAsRead: (id) =>
    set((state) => {
      const updated = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n,
      );
      return { notifications: updated, unreadCount: computeUnreadCount(updated) };
    }),

  markAllAsRead: () =>
    set((state) => {
      const updated = state.notifications.map((n) => ({ ...n, read: true }));
      return { notifications: updated, unreadCount: 0 };
    }),

  removeNotification: (id) =>
    set((state) => {
      const updated = state.notifications.filter((n) => n.id !== id);
      return { notifications: updated, unreadCount: computeUnreadCount(updated) };
    }),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),

  setOpen: (isOpen) => set({ isOpen }),

  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),
}));
