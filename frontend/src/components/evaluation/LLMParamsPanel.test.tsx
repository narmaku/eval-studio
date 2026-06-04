import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { LLMParamsPanel } from './LLMParamsPanel';
import type { LLMParams } from '@/types';

/** Wrapper that manages state so controlled inputs work correctly in tests. */
function Wrapper({
  initial = {},
  onChange,
  label,
}: {
  initial?: LLMParams;
  onChange?: (params: LLMParams) => void;
  label?: string;
}) {
  const [value, setValue] = useState<LLMParams>(initial);
  const handleChange = (next: LLMParams) => {
    setValue(next);
    onChange?.(next);
  };
  return <LLMParamsPanel label={label} value={value} onChange={handleChange} />;
}

describe('LLMParamsPanel', () => {
  it('renders the toggle button with default label', () => {
    render(<LLMParamsPanel value={{}} onChange={vi.fn()} />);
    expect(screen.getByText('Advanced Parameters')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<LLMParamsPanel label="Model Parameters" value={{}} onChange={vi.fn()} />);
    expect(screen.getByText('Model Parameters')).toBeInTheDocument();
  });

  it('shows parameter inputs when expanded', async () => {
    const user = userEvent.setup();
    render(<LLMParamsPanel value={{}} onChange={vi.fn()} />);

    await user.click(screen.getByText('Advanced Parameters'));

    expect(screen.getByLabelText('Max Tokens')).toBeInTheDocument();
    expect(screen.getByLabelText('Temperature')).toBeInTheDocument();
    expect(screen.getByLabelText('Top P')).toBeInTheDocument();
    expect(screen.getByLabelText('Frequency Penalty')).toBeInTheDocument();
    expect(screen.getByLabelText('Presence Penalty')).toBeInTheDocument();
  });

  it('displays existing values', async () => {
    const user = userEvent.setup();
    render(
      <LLMParamsPanel
        value={{ max_tokens: 2048, temperature: 0.7 }}
        onChange={vi.fn()}
      />,
    );

    // Badge should show "2 set"
    expect(screen.getByText('2 set')).toBeInTheDocument();

    await user.click(screen.getByText('Advanced Parameters'));

    expect(screen.getByLabelText('Max Tokens')).toHaveValue(2048);
    expect(screen.getByLabelText('Temperature')).toHaveValue(0.7);
  });

  it('calls onChange with updated value when input changes', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Wrapper onChange={onChange} />);

    await user.click(screen.getByText('Advanced Parameters'));
    await user.type(screen.getByLabelText('Max Tokens'), '1024');

    // onChange should have been called (multiple times during typing)
    expect(onChange).toHaveBeenCalled();
    // The last call should have max_tokens set to 1024
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1]![0] as Record<
      string,
      number
    >;
    expect(lastCall.max_tokens).toBe(1024);
  });

  it('removes param from value when input is cleared', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Wrapper initial={{ temperature: 0.7 }} onChange={onChange} />);

    await user.click(screen.getByText('Advanced Parameters'));
    const tempInput = screen.getByLabelText('Temperature');
    await user.clear(tempInput);

    // The last call should have temperature removed
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1]![0] as Record<
      string,
      number
    >;
    expect(lastCall).not.toHaveProperty('temperature');
  });

  it('does not show badge when no params are set', () => {
    render(<LLMParamsPanel value={{}} onChange={vi.fn()} />);
    expect(screen.queryByText(/set$/)).not.toBeInTheDocument();
  });
});
