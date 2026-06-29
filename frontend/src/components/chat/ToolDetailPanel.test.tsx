import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ToolDetailPanel } from './ToolDetailPanel';
import type { ToolCall } from '@/types';

const makeToolCall = (overrides: Partial<ToolCall> = {}): ToolCall => ({
  id: 'tc-1',
  tool_name: 'search_files',
  arguments: { query: 'test', path: '/var/log' },
  result: { matches: ['file1.txt', 'file2.txt'] },
  duration_ms: 245,
  timestamp: '2026-01-01T00:00:01Z',
  status: 'completed',
  ...overrides,
});

describe('ToolDetailPanel', () => {
  it('shows placeholder when no tool is selected', () => {
    render(<ToolDetailPanel toolCall={null} allToolCalls={[]} onSelect={vi.fn()} />);

    expect(screen.getByText(/click a tool call to inspect/i)).toBeInTheDocument();
  });

  it('shows tool name and status when a tool is selected', () => {
    const tc = makeToolCall();

    render(<ToolDetailPanel toolCall={tc} allToolCalls={[tc]} onSelect={vi.fn()} />);

    expect(screen.getByText('search_files')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  it('shows arguments section with JSON content', () => {
    const tc = makeToolCall();

    render(<ToolDetailPanel toolCall={tc} allToolCalls={[tc]} onSelect={vi.fn()} />);

    expect(screen.getByText('Arguments')).toBeInTheDocument();
    expect(screen.getByText(/test/)).toBeInTheDocument();
    expect(screen.getByText(/\/var\/log/)).toBeInTheDocument();
  });

  it('shows result section', () => {
    const tc = makeToolCall();

    render(<ToolDetailPanel toolCall={tc} allToolCalls={[tc]} onSelect={vi.fn()} />);

    expect(screen.getByText('Result')).toBeInTheDocument();
    expect(screen.getByText(/file1\.txt/)).toBeInTheDocument();
  });

  it('shows duration when available', () => {
    const tc = makeToolCall({ duration_ms: 2500 });

    render(<ToolDetailPanel toolCall={tc} allToolCalls={[tc]} onSelect={vi.fn()} />);

    expect(screen.getByText('2.5s')).toBeInTheDocument();
  });

  it('navigates to next tool call when next button is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
      makeToolCall({ id: 'tc-3', tool_name: 'write_file' }),
    ];

    render(
      <ToolDetailPanel toolCall={toolCalls[0]} allToolCalls={toolCalls} onSelect={onSelect} />,
    );

    const nextBtn = screen.getByRole('button', { name: /next tool/i });
    await user.click(nextBtn);

    expect(onSelect).toHaveBeenCalledWith(toolCalls[1]);
  });

  it('navigates to previous tool call when previous button is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
      makeToolCall({ id: 'tc-3', tool_name: 'write_file' }),
    ];

    render(
      <ToolDetailPanel toolCall={toolCalls[1]} allToolCalls={toolCalls} onSelect={onSelect} />,
    );

    const prevBtn = screen.getByRole('button', { name: /previous tool/i });
    await user.click(prevBtn);

    expect(onSelect).toHaveBeenCalledWith(toolCalls[0]);
  });

  it('disables previous button on first tool call', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
    ];

    render(<ToolDetailPanel toolCall={toolCalls[0]} allToolCalls={toolCalls} onSelect={vi.fn()} />);

    const prevBtn = screen.getByRole('button', { name: /previous tool/i });
    expect(prevBtn).toBeDisabled();
  });

  it('disables next button on last tool call', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
    ];

    render(<ToolDetailPanel toolCall={toolCalls[1]} allToolCalls={toolCalls} onSelect={vi.fn()} />);

    const nextBtn = screen.getByRole('button', { name: /next tool/i });
    expect(nextBtn).toBeDisabled();
  });

  it('shows mini tool list pills for quick switching', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const toolCalls = [
      makeToolCall({ id: 'tc-1', tool_name: 'search_files' }),
      makeToolCall({ id: 'tc-2', tool_name: 'read_file' }),
    ];

    render(
      <ToolDetailPanel toolCall={toolCalls[0]} allToolCalls={toolCalls} onSelect={onSelect} />,
    );

    // Click on the mini pill for read_file
    const pill = screen.getByTestId('tool-pill-tc-2');
    await user.click(pill);

    expect(onSelect).toHaveBeenCalledWith(toolCalls[1]);
  });

  it('shows position indicator (e.g., "1 of 3")', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1' }),
      makeToolCall({ id: 'tc-2' }),
      makeToolCall({ id: 'tc-3' }),
    ];

    render(<ToolDetailPanel toolCall={toolCalls[1]} allToolCalls={toolCalls} onSelect={vi.fn()} />);

    expect(screen.getByText('2 of 3')).toBeInTheDocument();
  });

  it('shows string result as plain text', () => {
    const tc = makeToolCall({ result: 'plain text output' });

    render(<ToolDetailPanel toolCall={tc} allToolCalls={[tc]} onSelect={vi.fn()} />);

    expect(screen.getByText('plain text output')).toBeInTheDocument();
  });

  it('shows spinner icon for executing status', () => {
    const tc = makeToolCall({ status: 'executing' });

    render(<ToolDetailPanel toolCall={tc} allToolCalls={[tc]} onSelect={vi.fn()} />);

    expect(screen.getByText('executing')).toBeInTheDocument();
  });
});
