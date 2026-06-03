import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { ToolCallCard } from './ToolCallCard';
import type { ToolCall } from '@/types';

const mockToolCall: ToolCall = {
  id: 'tc-1',
  tool_name: 'search_files',
  arguments: { query: 'test query', path: '/var/log' },
  result: { matches: ['file1.txt', 'file2.txt'] },
  duration_ms: 245,
  timestamp: '2026-01-01T00:00:01Z',
};

describe('ToolCallCard', () => {
  it('renders tool name when collapsed', () => {
    render(<ToolCallCard toolCall={mockToolCall} />);

    expect(screen.getByText('search_files')).toBeInTheDocument();
  });

  it('shows duration badge', () => {
    render(<ToolCallCard toolCall={mockToolCall} />);

    expect(screen.getByText('245ms')).toBeInTheDocument();
  });

  it('does not show arguments when collapsed', () => {
    render(<ToolCallCard toolCall={mockToolCall} />);

    // Arguments should not be visible initially
    expect(screen.queryByText('"test query"')).not.toBeInTheDocument();
  });

  it('shows arguments and result when expanded', async () => {
    const user = userEvent.setup();
    render(<ToolCallCard toolCall={mockToolCall} />);

    // Click to expand
    const trigger = screen.getByRole('button', { name: /search_files/i });
    await user.click(trigger);

    // Arguments and result should now be visible
    expect(screen.getByText(/test query/)).toBeInTheDocument();
    expect(screen.getByText(/file1\.txt/)).toBeInTheDocument();
  });

  it('formats duration in seconds when over 1000ms', () => {
    const longToolCall: ToolCall = {
      ...mockToolCall,
      duration_ms: 2500,
    };

    render(<ToolCallCard toolCall={longToolCall} />);

    expect(screen.getByText('2.5s')).toBeInTheDocument();
  });

  it('shows "Show in chat" button when message_id is present and expanded', async () => {
    const user = userEvent.setup();
    const toolCallWithMessageId: ToolCall = {
      ...mockToolCall,
      message_id: 'msg-123',
    };

    render(<ToolCallCard toolCall={toolCallWithMessageId} />);

    // Expand the card
    const trigger = screen.getByRole('button', { name: /search_files/i });
    await user.click(trigger);

    expect(screen.getByText('Show in chat')).toBeInTheDocument();
  });

  it('does not show "Show in chat" button when no message_id', async () => {
    const user = userEvent.setup();
    render(<ToolCallCard toolCall={mockToolCall} />);

    // Expand the card
    const trigger = screen.getByRole('button', { name: /search_files/i });
    await user.click(trigger);

    expect(screen.queryByText('Show in chat')).not.toBeInTheDocument();
  });

  it('accepts messageId prop to override toolCall.message_id', async () => {
    const user = userEvent.setup();
    render(<ToolCallCard toolCall={mockToolCall} messageId="msg-override" />);

    // Expand the card
    const trigger = screen.getByRole('button', { name: /search_files/i });
    await user.click(trigger);

    expect(screen.getByText('Show in chat')).toBeInTheDocument();
  });
});
