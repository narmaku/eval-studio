import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ToolSidePanel } from './ToolSidePanel';
import type { ToolCall } from '@/types';

const mockToolCalls: ToolCall[] = [
  {
    id: 'tc-1',
    tool_name: 'search_files',
    arguments: { query: 'test' },
    result: { matches: [] },
    duration_ms: 100,
    timestamp: '2026-01-01T00:00:00Z',
    message_id: 'msg-1',
    status: 'completed',
  },
  {
    id: 'tc-2',
    tool_name: 'read_file',
    arguments: { path: '/etc/hosts' },
    result: 'contents',
    duration_ms: 50,
    timestamp: '2026-01-01T00:00:01Z',
    message_id: 'msg-2',
    status: 'completed',
  },
];

describe('ToolSidePanel', () => {
  it('renders with inspection panel visible by default', () => {
    render(
      <ToolSidePanel toolCalls={mockToolCalls} selectedToolId={null} onToolSelect={vi.fn()} />,
    );

    // Should show the placeholder text when no tool selected
    expect(screen.getByText(/click a tool call to inspect/i)).toBeInTheDocument();
  });

  it('shows selected tool details when a tool is selected', () => {
    render(
      <ToolSidePanel toolCalls={mockToolCalls} selectedToolId="tc-1" onToolSelect={vi.fn()} />,
    );

    // Tool name appears in both the mini pill bar and the header
    expect(screen.getAllByText('search_files').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Arguments')).toBeInTheDocument();
  });

  it('collapses when toggle button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <ToolSidePanel toolCalls={mockToolCalls} selectedToolId={null} onToolSelect={vi.fn()} />,
    );

    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    // Panel content should be hidden
    expect(screen.queryByText(/click a tool call to inspect/i)).not.toBeInTheDocument();
  });

  it('shows tool call count badge when collapsed', async () => {
    const user = userEvent.setup();
    render(
      <ToolSidePanel toolCalls={mockToolCalls} selectedToolId={null} onToolSelect={vi.fn()} />,
    );

    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('expands when toggle button is clicked while collapsed', async () => {
    const user = userEvent.setup();
    render(
      <ToolSidePanel toolCalls={mockToolCalls} selectedToolId={null} onToolSelect={vi.fn()} />,
    );

    // Collapse
    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    // Expand
    const expandBtn = screen.getByRole('button', { name: /expand tool panel/i });
    await user.click(expandBtn);

    expect(screen.getByText(/click a tool call to inspect/i)).toBeInTheDocument();
  });

  it('does not show badge when collapsed with no tool calls', async () => {
    const user = userEvent.setup();
    render(<ToolSidePanel toolCalls={[]} selectedToolId={null} onToolSelect={vi.fn()} />);

    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    // No badge should appear for 0 tool calls
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('passes onToolSelect to ToolDetailPanel for navigation', async () => {
    const user = userEvent.setup();
    const onToolSelect = vi.fn();
    render(
      <ToolSidePanel toolCalls={mockToolCalls} selectedToolId="tc-1" onToolSelect={onToolSelect} />,
    );

    // Click next button to navigate
    const nextBtn = screen.getByRole('button', { name: /next tool/i });
    await user.click(nextBtn);

    expect(onToolSelect).toHaveBeenCalledWith(mockToolCalls[1]);
  });
});
