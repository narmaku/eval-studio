import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { NotificationPanel } from './NotificationPanel';
import { useNotificationStore } from '@/stores/notificationStore';

function renderPanel() {
  return render(
    <MemoryRouter>
      <NotificationPanel />
    </MemoryRouter>,
  );
}

describe('NotificationPanel', () => {
  beforeEach(() => {
    useNotificationStore.setState({
      notifications: [],
      unreadCount: 0,
      isOpen: false,
    });
  });

  it('does not render panel content when closed', () => {
    renderPanel();
    expect(screen.queryByText('Notifications')).not.toBeInTheDocument();
  });

  it('renders empty state when open with no notifications', () => {
    useNotificationStore.setState({ isOpen: true });
    renderPanel();

    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('No notifications yet')).toBeInTheDocument();
  });

  it('does not show action buttons when there are no notifications', () => {
    useNotificationStore.setState({ isOpen: true });
    renderPanel();

    expect(screen.queryByText('Mark all read')).not.toBeInTheDocument();
    expect(screen.queryByText('Clear all')).not.toBeInTheDocument();
  });

  it('renders notification cards when notifications exist', () => {
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 2,
      notifications: [
        {
          id: '1',
          type: 'success',
          title: 'Evaluation Completed',
          message: 'Finished with 95% accuracy',
          timestamp: new Date(),
          read: false,
        },
        {
          id: '2',
          type: 'error',
          title: 'Evaluation Failed',
          message: 'Connection timeout',
          timestamp: new Date(),
          read: false,
        },
      ],
    });

    renderPanel();

    expect(screen.getByText('Evaluation Completed')).toBeInTheDocument();
    expect(screen.getByText('Finished with 95% accuracy')).toBeInTheDocument();
    expect(screen.getByText('Evaluation Failed')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });

  it('shows "Mark all read" button when there are unread notifications', () => {
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 1,
      notifications: [
        {
          id: '1',
          type: 'info',
          title: 'Test',
          message: 'msg',
          timestamp: new Date(),
          read: false,
        },
      ],
    });

    renderPanel();
    expect(screen.getByText('Mark all read')).toBeInTheDocument();
  });

  it('shows "Clear all" button when notifications exist', () => {
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 0,
      notifications: [
        {
          id: '1',
          type: 'info',
          title: 'Test',
          message: 'msg',
          timestamp: new Date(),
          read: true,
        },
      ],
    });

    renderPanel();
    expect(screen.getByText('Clear all')).toBeInTheDocument();
  });

  it('marks all as read when "Mark all read" is clicked', async () => {
    const user = userEvent.setup();
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 2,
      notifications: [
        {
          id: '1',
          type: 'info',
          title: 'A',
          message: 'msg',
          timestamp: new Date(),
          read: false,
        },
        {
          id: '2',
          type: 'info',
          title: 'B',
          message: 'msg',
          timestamp: new Date(),
          read: false,
        },
      ],
    });

    renderPanel();
    await user.click(screen.getByText('Mark all read'));

    const state = useNotificationStore.getState();
    expect(state.unreadCount).toBe(0);
    state.notifications.forEach((n) => {
      expect(n.read).toBe(true);
    });
  });

  it('clears all notifications when "Clear all" is clicked', async () => {
    const user = userEvent.setup();
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 1,
      notifications: [
        {
          id: '1',
          type: 'info',
          title: 'A',
          message: 'msg',
          timestamp: new Date(),
          read: false,
        },
      ],
    });

    renderPanel();
    await user.click(screen.getByText('Clear all'));

    expect(useNotificationStore.getState().notifications).toEqual([]);
  });

  it('renders expandable details section when details are provided', async () => {
    const user = userEvent.setup();
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 1,
      notifications: [
        {
          id: '1',
          type: 'error',
          title: 'Error',
          message: 'Something broke',
          details: 'Error: Connection refused\n  at fetch()',
          timestamp: new Date(),
          read: false,
        },
      ],
    });

    renderPanel();

    // Details should not be visible initially
    expect(screen.queryByText('Error: Connection refused')).not.toBeInTheDocument();

    // Click the Details toggle
    await user.click(screen.getByText('Details'));

    // Details should now be visible
    expect(screen.getByText(/Error: Connection refused/)).toBeInTheDocument();
  });

  it('renders "View Results" link when evaluationId is set', () => {
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 1,
      notifications: [
        {
          id: '1',
          type: 'success',
          title: 'Done',
          message: 'msg',
          evaluationId: 'eval-abc',
          timestamp: new Date(),
          read: false,
        },
      ],
    });

    renderPanel();

    const link = screen.getByText('View Results');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/results/eval-abc');
  });

  it('shows relative timestamps', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 1,
      notifications: [
        {
          id: '1',
          type: 'info',
          title: 'Test',
          message: 'msg',
          timestamp: fiveMinutesAgo,
          read: false,
        },
      ],
    });

    renderPanel();
    expect(screen.getByText('5 minutes ago')).toBeInTheDocument();
  });

  it('marks notification as read when clicking on an unread card', async () => {
    const user = userEvent.setup();
    useNotificationStore.setState({
      isOpen: true,
      unreadCount: 1,
      notifications: [
        {
          id: 'n1',
          type: 'info',
          title: 'Test',
          message: 'msg',
          timestamp: new Date(),
          read: false,
        },
      ],
    });

    renderPanel();

    const card = screen.getByRole('article');
    await user.click(card);

    const state = useNotificationStore.getState();
    expect(state.notifications[0]!.read).toBe(true);
    expect(state.unreadCount).toBe(0);
  });
});
