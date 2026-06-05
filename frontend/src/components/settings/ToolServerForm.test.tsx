import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockCreateToolServer = vi.fn();
const mockUpdateToolServer = vi.fn();

vi.mock('@/stores/toolServerStore', () => ({
  useToolServerStore: (selector?: unknown) => {
    const state = {
      createToolServer: mockCreateToolServer,
      updateToolServer: mockUpdateToolServer,
    };
    if (typeof selector === 'function') {
      return (selector as (s: typeof state) => unknown)(state);
    }
    return state;
  },
}));

import { ToolServerForm } from './ToolServerForm';

describe('ToolServerForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form fields when open', () => {
    render(<ToolServerForm open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/command/i)).toBeInTheDocument();
  });

  it('displays backend error message when save fails', async () => {
    const user = userEvent.setup();
    mockCreateToolServer.mockRejectedValue(
      new Error("command '/usr/bin/uv' is not in the allowed list"),
    );

    render(<ToolServerForm open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByLabelText(/name/i), 'My Server');
    await user.type(screen.getByLabelText(/command/i), '/usr/bin/uv');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(
      screen.getByText("command '/usr/bin/uv' is not in the allowed list"),
    ).toBeInTheDocument();
  });

  it('displays generic fallback when error has no message', async () => {
    const user = userEvent.setup();
    mockCreateToolServer.mockRejectedValue(new Error());

    render(<ToolServerForm open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByLabelText(/name/i), 'My Server');
    await user.type(screen.getByLabelText(/command/i), 'echo');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(
      screen.getByText('Failed to save tool server. Please try again.'),
    ).toBeInTheDocument();
  });

  it('displays generic fallback for non-Error rejections', async () => {
    const user = userEvent.setup();
    mockCreateToolServer.mockRejectedValue('unexpected string error');

    render(<ToolServerForm open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByLabelText(/name/i), 'My Server');
    await user.type(screen.getByLabelText(/command/i), 'echo');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(
      screen.getByText('Failed to save tool server. Please try again.'),
    ).toBeInTheDocument();
  });
});
