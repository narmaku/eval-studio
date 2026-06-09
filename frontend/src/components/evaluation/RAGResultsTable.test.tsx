import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { RAGResultsTable } from './RAGResultsTable';
import type { Result, DatasetItem } from '@/types';

const mockResults: Result[] = [
  {
    id: 'r1',
    evaluation_id: 'e1',
    dataset_item_id: 'item-1',
    session_id: null,
    contestant_model: null,
    score: 0.85,
    passed: true,
    actual_answer: 'RHEL 9 supports Secure Boot on Nitro instances.',
    judge_reasoning: 'Accurate and well-sourced answer.',
    scores_breakdown: { faithfulness: 0.9, context_precision: 0.8, answer_relevance: 0.85 },
    retrieved_chunks: [{ content: 'Secure Boot is supported on Nitro.', score: 0.95 }],
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'r2',
    evaluation_id: 'e1',
    dataset_item_id: 'item-2',
    session_id: null,
    contestant_model: null,
    score: 0.4,
    passed: false,
    actual_answer: 'Check the docs.',
    judge_reasoning: 'Too vague, missing specific steps.',
    scores_breakdown: { faithfulness: 0.5, context_precision: 0.3, answer_relevance: 0.4 },
    retrieved_chunks: [],
    created_at: '2026-01-01T00:00:00Z',
  },
];

const mockDatasetItems: DatasetItem[] = [
  {
    id: 'item-1',
    question: 'How to configure RHEL on AWS with Secure Boot?',
    expected_answer: 'AWS supports Secure Boot for Nitro instances with RHEL AMIs.',
    metadata: {},
    order_index: 0,
  },
  {
    id: 'item-2',
    question: 'How to verify RHEL certification for AWS?',
    expected_answer: 'Visit the Red Hat Ecosystem Catalog certified cloud providers page.',
    metadata: {},
    order_index: 1,
  },
];

describe('RAGResultsTable', () => {
  it('renders all result rows', () => {
    render(<RAGResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    const rows = screen.getAllByRole('row');
    // 1 header + 2 data rows
    expect(rows).toHaveLength(3);
  });

  it('displays RAG metric columns', () => {
    render(<RAGResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    expect(screen.getByText('Faithfulness')).toBeInTheDocument();
    expect(screen.getByText('Precision')).toBeInTheDocument();
    expect(screen.getByText('Relevance')).toBeInTheDocument();
  });

  it('displays question text from dataset items', () => {
    render(<RAGResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    expect(screen.getByText(/How to configure RHEL on AWS/)).toBeInTheDocument();
    expect(screen.getByText(/How to verify RHEL certification/)).toBeInTheDocument();
  });

  it('shows -- for expected answer when datasetItems is not provided', () => {
    render(<RAGResultsTable results={mockResults} />);

    const cells = document.querySelectorAll('td');
    const dashCells = Array.from(cells).filter((cell) => cell.textContent === '--');
    expect(dashCells.length).toBeGreaterThan(0);
  });

  it('shows expected answer text when datasetItems is provided', () => {
    render(<RAGResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    expect(screen.getByText(/AWS supports Secure Boot for Nitro/)).toBeInTheDocument();
  });

  it('expands row on chevron click to show judge reasoning', async () => {
    const user = userEvent.setup();
    render(<RAGResultsTable results={mockResults} datasetItems={mockDatasetItems} />);

    const expandButtons = screen.getAllByRole('button', { name: /expand row/i });
    expect(expandButtons.length).toBeGreaterThan(0);

    await user.click(expandButtons[0]!);

    expect(screen.getByText(/Accurate and well-sourced answer/)).toBeInTheDocument();
  });

  it('calls onRowClick when a row is clicked', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();
    render(
      <RAGResultsTable
        results={mockResults}
        datasetItems={mockDatasetItems}
        onRowClick={onRowClick}
      />,
    );

    const rows = screen.getAllByRole('row');
    await user.click(rows[1]!);

    expect(onRowClick).toHaveBeenCalledWith(mockResults[0]);
  });

  it('shows empty state when no results are provided', () => {
    render(<RAGResultsTable results={[]} />);

    expect(screen.getByText('No results to display.')).toBeInTheDocument();
  });
});
