import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import type { Result } from '@/types';

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

// Use vi.hoisted for mocks referenced in hoisted vi.mock factories
const { mockExportResultsPdf, mockToastError } = vi.hoisted(() => ({
  mockExportResultsPdf: vi.fn(() => Promise.resolve()),
  mockToastError: vi.fn(),
}));

vi.mock('@/lib/exportPdf', () => ({
  exportResultsPdf: mockExportResultsPdf,
}));

vi.mock('sonner', () => ({
  toast: { error: mockToastError },
}));

import { ResultDetailView } from './ResultDetailView';

const makeResult = (id: string, score: number): Result => ({
  id,
  evaluation_id: 'eval-1',
  dataset_item_id: `item-${id}`,
  session_id: null,
  contestant_model: null,
  score,
  passed: score >= 0.5,
  actual_answer: 'test answer',
  judge_reasoning: 'reasoning',
  scores_breakdown: null,
  retrieved_chunks: null,
  created_at: '2026-01-01T00:00:00Z',
});

const defaultProps = {
  results: [makeResult('r1', 0.8), makeResult('r2', 0.6)],
  aggregateMetrics: {
    total_items: 2,
    passed_items: 2,
    failed_items: 0,
    mean_score: 0.7,
    median_score: 0.7,
    pass_rate: 1.0,
    score_distribution: {},
  },
  evaluationName: 'Test Evaluation',
  evaluationMode: 'qa' as const,
};

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('ResultDetailView — PDF export', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the Export PDF button', () => {
    renderWithRouter(<ResultDetailView {...defaultProps} />);
    expect(screen.getByRole('button', { name: /export pdf/i })).toBeInTheDocument();
  });

  it('calls exportResultsPdf when the button is clicked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ResultDetailView {...defaultProps} />);

    const button = screen.getByRole('button', { name: /export pdf/i });
    await user.click(button);

    expect(mockExportResultsPdf).toHaveBeenCalledTimes(1);
    expect(mockExportResultsPdf).toHaveBeenCalledWith(expect.any(HTMLElement), 'Test Evaluation');
  });

  it('disables the button while exporting', async () => {
    // Make the export hang so we can observe loading state
    let resolveExport: () => void = () => {};
    mockExportResultsPdf.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveExport = resolve;
        }),
    );

    const user = userEvent.setup();
    renderWithRouter(<ResultDetailView {...defaultProps} />);

    const button = screen.getByRole('button', { name: /export pdf/i });
    await user.click(button);

    expect(button).toBeDisabled();

    // Resolve the export
    resolveExport();
    // Wait for state to settle
    await vi.waitFor(() => expect(button).not.toBeDisabled());
  });

  it('shows a toast error when export fails', async () => {
    mockExportResultsPdf.mockRejectedValueOnce(new Error('Export failed'));

    const user = userEvent.setup();
    renderWithRouter(<ResultDetailView {...defaultProps} />);

    const button = screen.getByRole('button', { name: /export pdf/i });
    await user.click(button);

    await vi.waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith('Failed to export PDF. Please try again.');
    });
  });

  it('marks the back link with data-no-print', () => {
    renderWithRouter(<ResultDetailView {...defaultProps} />);
    const backLink = screen.getByText('Back to Results').closest('a');
    expect(backLink).toHaveAttribute('data-no-print');
  });

  it('marks the export button with data-no-print', () => {
    renderWithRouter(<ResultDetailView {...defaultProps} />);
    const button = screen.getByRole('button', { name: /export pdf/i });
    // The button or its container should have data-no-print
    const noPrintAncestor = button.closest('[data-no-print]');
    expect(noPrintAncestor).toBeInTheDocument();
  });

  it('renders export button in arena mode too', () => {
    renderWithRouter(
      <ResultDetailView
        {...defaultProps}
        evaluationMode="arena"
        arenaLeaderboard={{
          evaluation_id: 'eval-1',
          evaluation_name: 'Arena Test',
          contestants: [],
        }}
      />,
    );
    expect(screen.getByRole('button', { name: /export pdf/i })).toBeInTheDocument();
  });
});
