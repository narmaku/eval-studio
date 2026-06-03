import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ConversationPanel } from './ConversationPanel';
import type { Message } from '@/types';

const mockMessages: Message[] = [
  {
    id: 'msg-1',
    sender: 'user',
    content: 'Hello agent',
    timestamp: '2026-01-01T00:00:00Z',
  },
  {
    id: 'msg-2',
    sender: 'agent',
    content: 'Hello! How can I help you?',
    timestamp: '2026-01-01T00:00:01Z',
  },
  {
    id: 'msg-3',
    sender: 'system',
    content: 'Session started',
    timestamp: '2026-01-01T00:00:02Z',
  },
];

describe('ConversationPanel', () => {
  it('renders messages for each sender type', () => {
    render(
      <ConversationPanel
        messages={mockMessages}
        isProcessing={false}
        onSend={vi.fn()}
        disabled={false}
      />,
    );

    expect(screen.getByText('Hello agent')).toBeInTheDocument();
    expect(screen.getByText('Hello! How can I help you?')).toBeInTheDocument();
    expect(screen.getByText('Session started')).toBeInTheDocument();
  });

  it('hides chat input when disabled prop is true', () => {
    render(
      <ConversationPanel messages={[]} isProcessing={false} onSend={vi.fn()} disabled={true} />,
    );

    expect(screen.queryByPlaceholderText('Type a message...')).not.toBeInTheDocument();
  });

  it('disables chat input when isProcessing is true', () => {
    render(
      <ConversationPanel messages={[]} isProcessing={true} onSend={vi.fn()} disabled={false} />,
    );

    const textarea = screen.getByPlaceholderText('Type a message...');
    expect(textarea).toBeDisabled();
  });

  it('calls onSend when Enter is pressed with content', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();

    render(
      <ConversationPanel messages={[]} isProcessing={false} onSend={onSend} disabled={false} />,
    );

    const textarea = screen.getByPlaceholderText('Type a message...');
    await user.type(textarea, 'Test message');
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });

    expect(onSend).toHaveBeenCalledWith('Test message');
  });

  it('shows typing indicator when isProcessing is true', () => {
    render(
      <ConversationPanel messages={[]} isProcessing={true} onSend={vi.fn()} disabled={false} />,
    );

    expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();
  });

  it('does not show typing indicator when isProcessing is false', () => {
    render(
      <ConversationPanel messages={[]} isProcessing={false} onSend={vi.fn()} disabled={false} />,
    );

    expect(screen.queryByTestId('typing-indicator')).not.toBeInTheDocument();
  });

  it('renders empty state when no messages', () => {
    render(
      <ConversationPanel messages={[]} isProcessing={false} onSend={vi.fn()} disabled={false} />,
    );

    expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
  });
});
