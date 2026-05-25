import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { EvaluationResultsList } from './EvaluationResultsList';
import type { EvaluationResultRow } from './EvaluationResultsList';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

const mockRows: EvaluationResultRow[] = [
  {
    evaluationId: 'e1',
    resultId: 'r1',
    name: 'QA Benchmark v1',
    mode: 'qa',
    status: 'completed',
    totalItems: 10,
    passRate: 0.8,
    meanScore: 0.85,
    createdAt: '2026-01-15T10:00:00Z',
  },
  {
    evaluationId: 'e2',
    resultId: 'r2',
    name: 'RAG Evaluation',
    mode: 'rag',
    status: 'completed',
    totalItems: 20,
    passRate: 0.95,
    meanScore: 0.92,
    createdAt: '2026-01-10T10:00:00Z',
  },
  {
    evaluationId: 'e3',
    resultId: 'r3',
    name: 'Agent Test',
    mode: 'agent',
    status: 'completed',
    totalItems: 5,
    passRate: 0.6,
    meanScore: 0.65,
    createdAt: '2026-01-20T10:00:00Z',
  },
];

describe('EvaluationResultsList', () => {
  it('renders table with data', () => {
    render(<EvaluationResultsList rows={mockRows} />);

    // Check column headers
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Mode')).toBeInTheDocument();
    expect(screen.getByText('Items Scored')).toBeInTheDocument();
    expect(screen.getByText('Pass Rate')).toBeInTheDocument();
    expect(screen.getByText('Mean Score')).toBeInTheDocument();
    expect(screen.getByText('Date')).toBeInTheDocument();

    // Check row content
    expect(screen.getByText('QA Benchmark v1')).toBeInTheDocument();
    expect(screen.getByText('RAG Evaluation')).toBeInTheDocument();
    expect(screen.getByText('Agent Test')).toBeInTheDocument();
  });

  it('renders empty state when no rows provided', () => {
    render(<EvaluationResultsList rows={[]} />);
    expect(screen.getByText('No evaluation results yet.')).toBeInTheDocument();
  });

  it('formats pass rate as percentage', () => {
    render(<EvaluationResultsList rows={mockRows} />);
    expect(screen.getByText('80.0%')).toBeInTheDocument();
    expect(screen.getByText('95.0%')).toBeInTheDocument();
  });

  it('formats mean score to 3 decimals', () => {
    render(<EvaluationResultsList rows={mockRows} />);
    expect(screen.getByText('0.850')).toBeInTheDocument();
    expect(screen.getByText('0.920')).toBeInTheDocument();
  });

  it('navigates on row click', async () => {
    const user = userEvent.setup();
    render(<EvaluationResultsList rows={mockRows} />);

    const rows = screen.getAllByRole('row');
    // First row is the header; default sort is date desc, so first data row is Agent Test (r3, Jan 20)
    await user.click(rows[1]!);

    expect(mockNavigate).toHaveBeenCalledWith('/results/r3');
  });

  it('renders mode badges', () => {
    render(<EvaluationResultsList rows={mockRows} />);

    const badges = screen.getAllByText(/^(Q&A|RAG|Agent)$/i);
    expect(badges.length).toBeGreaterThanOrEqual(3);
  });

  it('displays correct item counts', () => {
    render(<EvaluationResultsList rows={mockRows} />);
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});
