import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ResultComparison from './ResultComparison';

const mockNavigate = vi.fn();
let mockSearchParams = new URLSearchParams('ids=e1&ids=e2&ref=e1');

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useSearchParams: () => [mockSearchParams],
}));

const mockFetchComparison = vi.fn();
const mockClearSelection = vi.fn();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SelectorFn = (state: any) => unknown;

const defaultStoreState = {
  comparisonData: null,
  isLoading: false,
  error: null,
  fetchComparison: mockFetchComparison,
  clearSelection: mockClearSelection,
};

vi.mock('@/stores/resultStore', () => ({
  useResultStore: vi.fn((selector: SelectorFn) => selector(defaultStoreState)),
}));

import { useResultStore } from '@/stores/resultStore';
const mockedUseResultStore = vi.mocked(useResultStore);

function mockStoreWith(overrides: Record<string, unknown>) {
  const state = { ...defaultStoreState, ...overrides };
  mockedUseResultStore.mockImplementation((selector: SelectorFn) => selector(state));
}

describe('ResultComparison', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams('ids=e1&ids=e2&ref=e1');
    mockedUseResultStore.mockImplementation((selector: SelectorFn) => selector(defaultStoreState));
  });

  it('calls fetchComparison on mount with URL params', () => {
    render(<ResultComparison />);
    expect(mockFetchComparison).toHaveBeenCalledWith(['e1', 'e2'], 'e1');
  });

  it('shows loading state', () => {
    mockStoreWith({ isLoading: true });
    render(<ResultComparison />);
    expect(screen.getByText(/loading comparison/i)).toBeInTheDocument();
  });

  it('shows error state', () => {
    mockStoreWith({ error: 'Incompatible evaluations' });
    render(<ResultComparison />);
    expect(screen.getByText(/incompatible evaluations/i)).toBeInTheDocument();
  });

  it('renders leaderboard when comparison data is available', () => {
    mockStoreWith({
      comparisonData: {
        evaluations: [
          {
            evaluation_id: 'e1',
            evaluation_name: 'Eval A',
            total_items: 10,
            passed_count: 8,
            failed_count: 2,
            average_score: 0.85,
            min_score: 0.5,
            max_score: 1.0,
            results: [],
          },
          {
            evaluation_id: 'e2',
            evaluation_name: 'Eval B',
            total_items: 10,
            passed_count: 6,
            failed_count: 4,
            average_score: 0.72,
            min_score: 0.3,
            max_score: 0.95,
            results: [],
          },
        ],
        item_comparisons: [],
        reference_evaluation_id: 'e1',
      },
    });

    render(<ResultComparison />);
    expect(screen.getByText('Eval A')).toBeInTheDocument();
    expect(screen.getByText('Eval B')).toBeInTheDocument();
    expect(screen.getByText('Evaluation Comparison')).toBeInTheDocument();
  });

  it('renders per-item comparison grid when items exist', () => {
    mockStoreWith({
      comparisonData: {
        evaluations: [
          {
            evaluation_id: 'e1',
            evaluation_name: 'Eval A',
            total_items: 1,
            passed_count: 1,
            failed_count: 0,
            average_score: 0.9,
            min_score: 0.9,
            max_score: 0.9,
            results: [],
          },
          {
            evaluation_id: 'e2',
            evaluation_name: 'Eval B',
            total_items: 1,
            passed_count: 0,
            failed_count: 1,
            average_score: 0.4,
            min_score: 0.4,
            max_score: 0.4,
            results: [],
          },
        ],
        item_comparisons: [
          {
            dataset_item_id: 'item-1',
            results: [
              {
                id: 'r1',
                evaluation_id: 'e1',
                dataset_item_id: 'item-1',
                session_id: null,
                contestant_model: null,
                score: 0.9,
                passed: true,
                actual_answer: 'Answer A',
                judge_reasoning: 'Good',
                scores_breakdown: null,
                retrieved_chunks: null,
                created_at: '2026-01-01T00:00:00Z',
              },
              {
                id: 'r2',
                evaluation_id: 'e2',
                dataset_item_id: 'item-1',
                session_id: null,
                contestant_model: null,
                score: 0.4,
                passed: false,
                actual_answer: 'Answer B',
                judge_reasoning: 'Poor',
                scores_breakdown: null,
                retrieved_chunks: null,
                created_at: '2026-01-01T00:00:00Z',
              },
            ],
          },
        ],
        reference_evaluation_id: 'e1',
      },
    });

    render(<ResultComparison />);
    expect(screen.getByText(/per-item comparison/i)).toBeInTheDocument();
    expect(screen.getByText('item-1')).toBeInTheDocument();
  });

  it('renders back button', () => {
    render(<ResultComparison />);
    expect(screen.getByText(/back to results/i)).toBeInTheDocument();
  });

  it('does not call fetchComparison when fewer than 2 evaluation IDs in URL', () => {
    mockSearchParams = new URLSearchParams('ids=e1');
    render(<ResultComparison />);
    expect(mockFetchComparison).not.toHaveBeenCalled();
  });

  it('calls fetchComparison without reference when ref param is absent', () => {
    mockSearchParams = new URLSearchParams('ids=e1&ids=e2');
    render(<ResultComparison />);
    expect(mockFetchComparison).toHaveBeenCalledWith(['e1', 'e2'], undefined);
  });

  it('shows Reference badge on the reference evaluation in leaderboard', () => {
    mockStoreWith({
      comparisonData: {
        evaluations: [
          {
            evaluation_id: 'e1',
            evaluation_name: 'Eval A',
            total_items: 10,
            passed_count: 8,
            failed_count: 2,
            average_score: 0.85,
            min_score: 0.5,
            max_score: 1.0,
            results: [],
          },
          {
            evaluation_id: 'e2',
            evaluation_name: 'Eval B',
            total_items: 10,
            passed_count: 6,
            failed_count: 4,
            average_score: 0.72,
            min_score: 0.3,
            max_score: 0.95,
            results: [],
          },
        ],
        item_comparisons: [],
        reference_evaluation_id: 'e1',
      },
    });

    render(<ResultComparison />);
    expect(screen.getByText('Reference')).toBeInTheDocument();
  });

  it('sorts leaderboard by average_score descending', () => {
    mockStoreWith({
      comparisonData: {
        evaluations: [
          {
            evaluation_id: 'e1',
            evaluation_name: 'Low Scorer',
            total_items: 5,
            passed_count: 2,
            failed_count: 3,
            average_score: 0.4,
            min_score: 0.2,
            max_score: 0.6,
            results: [],
          },
          {
            evaluation_id: 'e2',
            evaluation_name: 'High Scorer',
            total_items: 5,
            passed_count: 5,
            failed_count: 0,
            average_score: 0.95,
            min_score: 0.9,
            max_score: 1.0,
            results: [],
          },
        ],
        item_comparisons: [],
        reference_evaluation_id: null,
      },
    });

    render(<ResultComparison />);
    const rows = screen.getAllByRole('row');
    // row[0] is header, row[1] should be High Scorer (#1), row[2] should be Low Scorer (#2)
    expect(rows[1]).toHaveTextContent('High Scorer');
    expect(rows[1]).toHaveTextContent('#1');
    expect(rows[2]).toHaveTextContent('Low Scorer');
    expect(rows[2]).toHaveTextContent('#2');
  });

  it('does not render per-item comparison grid when item_comparisons is empty', () => {
    mockStoreWith({
      comparisonData: {
        evaluations: [
          {
            evaluation_id: 'e1',
            evaluation_name: 'Eval A',
            total_items: 0,
            passed_count: 0,
            failed_count: 0,
            average_score: 0,
            min_score: null,
            max_score: null,
            results: [],
          },
          {
            evaluation_id: 'e2',
            evaluation_name: 'Eval B',
            total_items: 0,
            passed_count: 0,
            failed_count: 0,
            average_score: 0,
            min_score: null,
            max_score: null,
            results: [],
          },
        ],
        item_comparisons: [],
        reference_evaluation_id: null,
      },
    });

    render(<ResultComparison />);
    expect(screen.queryByText(/per-item comparison/i)).not.toBeInTheDocument();
  });

  it('displays comparison count in subtitle', () => {
    mockSearchParams = new URLSearchParams('ids=e1&ids=e2&ids=e3');
    render(<ResultComparison />);
    expect(screen.getByText(/comparing 3 evaluations/i)).toBeInTheDocument();
  });
});
