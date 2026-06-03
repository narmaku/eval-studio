import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
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
  it('renders with tool inspector visible by default', () => {
    render(<ToolSidePanel toolCalls={mockToolCalls} />);

    expect(screen.getByText('Tool Calls')).toBeInTheDocument();
    expect(screen.getByText('search_files')).toBeInTheDocument();
  });

  it('collapses when toggle button is clicked', async () => {
    const user = userEvent.setup();
    render(<ToolSidePanel toolCalls={mockToolCalls} />);

    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    // Tool inspector content should be hidden
    expect(screen.queryByText('Tool Calls')).not.toBeInTheDocument();
  });

  it('shows tool call count badge when collapsed', async () => {
    const user = userEvent.setup();
    render(<ToolSidePanel toolCalls={mockToolCalls} />);

    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('expands when toggle button is clicked while collapsed', async () => {
    const user = userEvent.setup();
    render(<ToolSidePanel toolCalls={mockToolCalls} />);

    // Collapse
    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    // Expand
    const expandBtn = screen.getByRole('button', { name: /expand tool panel/i });
    await user.click(expandBtn);

    expect(screen.getByText('Tool Calls')).toBeInTheDocument();
  });

  it('does not show badge when collapsed with no tool calls', async () => {
    const user = userEvent.setup();
    render(<ToolSidePanel toolCalls={[]} />);

    const collapseBtn = screen.getByRole('button', { name: /collapse tool panel/i });
    await user.click(collapseBtn);

    // No badge should appear for 0 tool calls
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });
});
