import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { FieldTooltip } from './FieldTooltip';

describe('FieldTooltip', () => {
  it('renders the info icon button', () => {
    render(<FieldTooltip description="Some help text" />);
    expect(screen.getByRole('button', { name: /field info/i })).toBeInTheDocument();
  });

  it('shows description text on hover', async () => {
    const user = userEvent.setup();
    render(<FieldTooltip description="This is a helpful tooltip" />);

    const trigger = screen.getByRole('button', { name: /field info/i });
    await user.hover(trigger);

    // Radix Tooltip renders the text in both the visible content and an
    // accessible hidden span, so use findAllByText and assert at least one.
    const elements = await screen.findAllByText('This is a helpful tooltip');
    expect(elements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders with different description text', () => {
    const { rerender } = render(<FieldTooltip description="First description" />);
    expect(screen.getByRole('button', { name: /field info/i })).toBeInTheDocument();

    rerender(<FieldTooltip description="Second description" />);
    expect(screen.getByRole('button', { name: /field info/i })).toBeInTheDocument();
  });
});
