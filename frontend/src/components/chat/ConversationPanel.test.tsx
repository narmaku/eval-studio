import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ConversationPanel } from './ConversationPanel';
import type { Message, ToolCall } from '@/types';

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

const makeToolCall = (overrides: Partial<ToolCall> = {}): ToolCall => ({
  id: 'tc-1',
  tool_name: 'search_files',
  arguments: { query: 'test' },
  result: { matches: [] },
  duration_ms: 100,
  timestamp: '2026-01-01T00:00:00Z',
  status: 'completed',
  ...overrides,
});

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

  describe('inline tool indicators', () => {
    it('renders tool indicators between messages grouped by message_id', () => {
      const toolCalls = [
        makeToolCall({ id: 'tc-1', tool_name: 'search_files', message_id: 'msg-2' }),
        makeToolCall({ id: 'tc-2', tool_name: 'read_file', message_id: 'msg-2' }),
      ];

      render(
        <ConversationPanel
          messages={mockMessages}
          isProcessing={false}
          onSend={vi.fn()}
          disabled={false}
          toolCalls={toolCalls}
          onToolSelect={vi.fn()}
        />,
      );

      expect(screen.getByTestId('tool-call-indicator')).toBeInTheDocument();
      expect(screen.getByText('search_files')).toBeInTheDocument();
      expect(screen.getByText('read_file')).toBeInTheDocument();
    });

    it('does not render indicators when toolCalls is not provided', () => {
      render(
        <ConversationPanel
          messages={mockMessages}
          isProcessing={false}
          onSend={vi.fn()}
          disabled={false}
        />,
      );

      expect(screen.queryByTestId('tool-call-indicator')).not.toBeInTheDocument();
    });

    it('calls onToolSelect when a tool chip is clicked', async () => {
      const user = userEvent.setup();
      const onToolSelect = vi.fn();
      const toolCalls = [
        makeToolCall({ id: 'tc-1', tool_name: 'search_files', message_id: 'msg-2' }),
      ];

      render(
        <ConversationPanel
          messages={mockMessages}
          isProcessing={false}
          onSend={vi.fn()}
          disabled={false}
          toolCalls={toolCalls}
          onToolSelect={onToolSelect}
        />,
      );

      await user.click(screen.getByText('search_files'));
      expect(onToolSelect).toHaveBeenCalledWith(toolCalls[0]);
    });

    it('passes selectedToolId to indicators', () => {
      const toolCalls = [
        makeToolCall({ id: 'tc-1', tool_name: 'search_files', message_id: 'msg-2' }),
      ];

      render(
        <ConversationPanel
          messages={mockMessages}
          isProcessing={false}
          onSend={vi.fn()}
          disabled={false}
          toolCalls={toolCalls}
          onToolSelect={vi.fn()}
          selectedToolId="tc-1"
        />,
      );

      const chip = screen.getByTestId('tool-chip-tc-1');
      expect(chip.className).toContain('ring-2');
    });

    it('groups tool calls without message_id with the most recent agent message', () => {
      const toolCalls = [
        makeToolCall({ id: 'tc-orphan', tool_name: 'orphan_tool', message_id: undefined }),
      ];

      render(
        <ConversationPanel
          messages={mockMessages}
          isProcessing={false}
          onSend={vi.fn()}
          disabled={false}
          toolCalls={toolCalls}
          onToolSelect={vi.fn()}
        />,
      );

      // The orphan tool should still be rendered as an indicator
      expect(screen.getByText('orphan_tool')).toBeInTheDocument();
    });
  });
});
