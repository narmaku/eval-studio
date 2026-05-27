import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { RAGMetricsSelector, ALL_RAG_METRICS } from './RAGMetricsSelector';

describe('RAGMetricsSelector', () => {
  it('renders all four metric checkboxes', () => {
    const onChange = vi.fn();
    render(<RAGMetricsSelector value={ALL_RAG_METRICS} onChange={onChange} />);

    expect(screen.getByText('Context Precision')).toBeInTheDocument();
    expect(screen.getByText('Context Recall')).toBeInTheDocument();
    expect(screen.getByText('Faithfulness')).toBeInTheDocument();
    expect(screen.getByText('Answer Relevance')).toBeInTheDocument();
  });

  it('renders metric descriptions', () => {
    const onChange = vi.fn();
    render(<RAGMetricsSelector value={ALL_RAG_METRICS} onChange={onChange} />);

    expect(screen.getByText('Are retrieved chunks relevant?')).toBeInTheDocument();
    expect(screen.getByText('Do chunks cover needed info?')).toBeInTheDocument();
    expect(screen.getByText('Is answer grounded in chunks?')).toBeInTheDocument();
    expect(screen.getByText('Does answer address the question?')).toBeInTheDocument();
  });

  it('shows all metrics as checked when all are in value', () => {
    const onChange = vi.fn();
    render(<RAGMetricsSelector value={ALL_RAG_METRICS} onChange={onChange} />);

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(4);
    checkboxes.forEach((cb) => {
      expect(cb).toBeChecked();
    });
  });

  it('shows unchecked metrics when not in value', () => {
    const onChange = vi.fn();
    render(<RAGMetricsSelector value={['faithfulness']} onChange={onChange} />);

    const checkboxes = screen.getAllByRole('checkbox');
    const checked = checkboxes.filter((cb) => (cb as HTMLInputElement).checked);
    expect(checked).toHaveLength(1);
  });

  it('removes metric from value when unchecking', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<RAGMetricsSelector value={ALL_RAG_METRICS} onChange={onChange} />);

    const faithfulnessCheckbox = screen.getByRole('checkbox', {
      name: /Faithfulness/,
    });
    await user.click(faithfulnessCheckbox);

    expect(onChange).toHaveBeenCalledWith(
      ALL_RAG_METRICS.filter((m) => m !== 'faithfulness'),
    );
  });

  it('adds metric to value when checking', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<RAGMetricsSelector value={['faithfulness']} onChange={onChange} />);

    const precisionCheckbox = screen.getByRole('checkbox', {
      name: /Context Precision/,
    });
    await user.click(precisionCheckbox);

    expect(onChange).toHaveBeenCalledWith(['faithfulness', 'context_precision']);
  });

  it('disables all checkboxes when disabled prop is true', () => {
    const onChange = vi.fn();
    render(
      <RAGMetricsSelector value={ALL_RAG_METRICS} onChange={onChange} disabled />,
    );

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((cb) => {
      expect(cb).toBeDisabled();
    });
  });

  it('displays card title', () => {
    const onChange = vi.fn();
    render(<RAGMetricsSelector value={ALL_RAG_METRICS} onChange={onChange} />);

    expect(screen.getByText('RAG Metrics')).toBeInTheDocument();
  });
});
