import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ToolCallIndicator } from './ToolCallIndicator';
import type { ToolCall } from '@/types';

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

describe('ToolCallIndicator', () => {
  it('renders tool names as clickable chips', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
    ];

    render(<ToolCallIndicator toolCalls={toolCalls} onSelect={vi.fn()} />);

    expect(screen.getByText('search_files')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
  });

  it('shows checkmark icon for completed status', () => {
    const toolCalls = [makeToolCall({ status: 'completed' })];
    const { container } = render(<ToolCallIndicator toolCalls={toolCalls} onSelect={vi.fn()} />);

    // Lucide renders SVGs with specific classes — look for the check-circle icon
    const checkIcon = container.querySelector('[data-testid="status-completed"]');
    expect(checkIcon).toBeInTheDocument();
  });

  it('shows spinner for executing status', () => {
    const toolCalls = [makeToolCall({ status: 'executing' })];
    const { container } = render(<ToolCallIndicator toolCalls={toolCalls} onSelect={vi.fn()} />);

    const spinnerIcon = container.querySelector('[data-testid="status-executing"]');
    expect(spinnerIcon).toBeInTheDocument();
  });

  it('shows error icon for error status', () => {
    const toolCalls = [makeToolCall({ status: 'error' })];
    const { container } = render(<ToolCallIndicator toolCalls={toolCalls} onSelect={vi.fn()} />);

    const errorIcon = container.querySelector('[data-testid="status-error"]');
    expect(errorIcon).toBeInTheDocument();
  });

  it('calls onSelect with the tool call when a chip is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
    ];

    render(<ToolCallIndicator toolCalls={toolCalls} onSelect={onSelect} />);

    await user.click(screen.getByText('read_file'));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(toolCalls[1]);
  });

  it('highlights the selected tool call chip', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
    ];

    render(<ToolCallIndicator toolCalls={toolCalls} onSelect={vi.fn()} selectedToolId="tc-2" />);

    const selectedChip = screen.getByTestId('tool-chip-tc-2');
    const unselectedChip = screen.getByTestId('tool-chip-tc-1');

    expect(selectedChip.className).toContain('ring-2');
    expect(unselectedChip.className).not.toContain('ring-2');
  });

  it('renders nothing when toolCalls is empty', () => {
    const { container } = render(<ToolCallIndicator toolCalls={[]} onSelect={vi.fn()} />);

    expect(container.firstChild).toBeNull();
  });
});
