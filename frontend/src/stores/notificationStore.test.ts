import { describe, it, expect, beforeEach } from 'vitest';
import { useNotificationStore } from './notificationStore';

describe('notificationStore', () => {
  beforeEach(() => {
    useNotificationStore.setState({
      notifications: [],
      unreadCount: 0,
      isOpen: false,
    });
  });

  it('has correct initial state', () => {
    const state = useNotificationStore.getState();
    expect(state.notifications).toEqual([]);
    expect(state.unreadCount).toBe(0);
    expect(state.isOpen).toBe(false);
  });

  describe('addNotification', () => {
    it('adds a notification with generated id, timestamp, and read=false', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({
        type: 'success',
        title: 'Evaluation Completed',
        message: 'Q&A eval finished with 95% accuracy',
      });

      const state = useNotificationStore.getState();
      expect(state.notifications).toHaveLength(1);

      const notification = state.notifications[0]!;
      expect(notification.id).toBeDefined();
      expect(notification.type).toBe('success');
      expect(notification.title).toBe('Evaluation Completed');
      expect(notification.message).toBe('Q&A eval finished with 95% accuracy');
      expect(notification.read).toBe(false);
      expect(notification.timestamp).toBeInstanceOf(Date);
    });

    it('increments unreadCount when adding a notification', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'First', message: 'msg' });
      expect(useNotificationStore.getState().unreadCount).toBe(1);

      addNotification({ type: 'error', title: 'Second', message: 'msg' });
      expect(useNotificationStore.getState().unreadCount).toBe(2);
    });

    it('prepends new notifications (newest first)', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'First', message: 'msg' });
      addNotification({ type: 'info', title: 'Second', message: 'msg' });

      const titles = useNotificationStore
        .getState()
        .notifications.map((n) => n.title);
      expect(titles).toEqual(['Second', 'First']);
    });

    it('preserves optional fields like details and evaluationId', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed',
        details: 'Stack trace here',
        evaluationId: 'eval-123',
      });

      const notification = state().notifications[0]!;
      expect(notification.details).toBe('Stack trace here');
      expect(notification.evaluationId).toBe('eval-123');
    });

    it('enforces maximum of 50 notifications by dropping oldest', () => {
      const { addNotification } = useNotificationStore.getState();

      for (let i = 0; i < 55; i++) {
        addNotification({
          type: 'info',
          title: `Notification ${i}`,
          message: 'msg',
        });
      }

      const s = state();
      expect(s.notifications).toHaveLength(50);
      // The newest should be at index 0
      expect(s.notifications[0]!.title).toBe('Notification 54');
      // The oldest remaining should be at the end
      expect(s.notifications[49]!.title).toBe('Notification 5');
    });
  });

  describe('markAsRead', () => {
    it('marks a specific notification as read', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'Test', message: 'msg' });
      const id = state().notifications[0]!.id;

      useNotificationStore.getState().markAsRead(id);

      const notification = state().notifications[0]!;
      expect(notification.read).toBe(true);
    });

    it('decrements unreadCount when marking as read', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'A', message: 'msg' });
      addNotification({ type: 'info', title: 'B', message: 'msg' });
      expect(state().unreadCount).toBe(2);

      const id = state().notifications[0]!.id;
      useNotificationStore.getState().markAsRead(id);
      expect(state().unreadCount).toBe(1);
    });

    it('does not affect other notifications', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'A', message: 'msg' });
      addNotification({ type: 'info', title: 'B', message: 'msg' });

      const notifications = state().notifications;
      useNotificationStore.getState().markAsRead(notifications[0]!.id);

      const updated = state().notifications;
      expect(updated[0]!.read).toBe(true);
      expect(updated[1]!.read).toBe(false);
    });

    it('is a no-op for non-existent ids', () => {
      const { addNotification } = useNotificationStore.getState();
      addNotification({ type: 'info', title: 'Test', message: 'msg' });

      useNotificationStore.getState().markAsRead('non-existent-id');

      expect(state().unreadCount).toBe(1);
      expect(state().notifications[0]!.read).toBe(false);
    });
  });

  describe('markAllAsRead', () => {
    it('marks all notifications as read and sets unreadCount to 0', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'A', message: 'msg' });
      addNotification({ type: 'error', title: 'B', message: 'msg' });
      addNotification({ type: 'success', title: 'C', message: 'msg' });

      useNotificationStore.getState().markAllAsRead();

      const s = state();
      expect(s.unreadCount).toBe(0);
      s.notifications.forEach((n) => {
        expect(n.read).toBe(true);
      });
    });
  });

  describe('removeNotification', () => {
    it('removes a notification by id', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'Keep', message: 'msg' });
      addNotification({ type: 'info', title: 'Remove', message: 'msg' });

      const toRemove = state().notifications.find((n) => n.title === 'Remove');
      expect(toRemove).toBeDefined();
      useNotificationStore.getState().removeNotification(toRemove!.id);

      const s = state();
      expect(s.notifications).toHaveLength(1);
      expect(s.notifications[0]!.title).toBe('Keep');
    });

    it('updates unreadCount when removing an unread notification', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'A', message: 'msg' });
      addNotification({ type: 'info', title: 'B', message: 'msg' });
      expect(state().unreadCount).toBe(2);

      const id = state().notifications[0]!.id;
      useNotificationStore.getState().removeNotification(id);
      expect(state().unreadCount).toBe(1);
    });
  });

  describe('clearAll', () => {
    it('removes all notifications and resets unreadCount', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'A', message: 'msg' });
      addNotification({ type: 'error', title: 'B', message: 'msg' });

      useNotificationStore.getState().clearAll();

      const s = state();
      expect(s.notifications).toEqual([]);
      expect(s.unreadCount).toBe(0);
    });
  });

  describe('panel open/close', () => {
    it('setOpen controls isOpen state', () => {
      useNotificationStore.getState().setOpen(true);
      expect(state().isOpen).toBe(true);

      useNotificationStore.getState().setOpen(false);
      expect(state().isOpen).toBe(false);
    });

    it('toggleOpen toggles isOpen state', () => {
      expect(state().isOpen).toBe(false);

      useNotificationStore.getState().toggleOpen();
      expect(state().isOpen).toBe(true);

      useNotificationStore.getState().toggleOpen();
      expect(state().isOpen).toBe(false);
    });
  });

  describe('crypto.randomUUID generates unique ids', () => {
    it('assigns unique ids to each notification', () => {
      const { addNotification } = useNotificationStore.getState();

      addNotification({ type: 'info', title: 'A', message: 'msg' });
      addNotification({ type: 'info', title: 'B', message: 'msg' });

      const ids = state().notifications.map((n) => n.id);
      expect(ids[0]).not.toBe(ids[1]);
    });
  });
});

/** Helper to reduce verbosity in assertions. */
function state() {
  return useNotificationStore.getState();
}
