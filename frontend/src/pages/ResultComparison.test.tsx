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

vi.mock('@/stores/resultStore', () => ({
  useResultStore: vi.fn((selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      comparisonData: null as Record<string, unknown> | null,
      isLoading: false,
      error: null as string | null,
      fetchComparison: mockFetchComparison,
      clearSelection: vi.fn(),
    };
    return selector(state);
  }),
}));

import { useResultStore } from '@/stores/resultStore';
const mockedUseResultStore = vi.mocked(useResultStore);

describe('ResultComparison', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams('ids=e1&ids=e2&ref=e1');
  });

  it('calls fetchComparison on mount with URL params', () => {
    render(<ResultComparison />);
    expect(mockFetchComparison).toHaveBeenCalledWith(['e1', 'e2'], 'e1');
  });

  it('shows loading state', () => {
    mockedUseResultStore.mockImplementation(
      (selector: (state: Record<string, unknown>) => unknown) => {
        const state = {
          comparisonData: null,
          isLoading: true,
          error: null,
          fetchComparison: mockFetchComparison,
          clearSelection: vi.fn(),
        };
        return selector(state);
      },
    );

    render(<ResultComparison />);
    expect(screen.getByText(/loading comparison/i)).toBeInTheDocument();
  });

  it('shows error state', () => {
    mockedUseResultStore.mockImplementation(
      (selector: (state: Record<string, unknown>) => unknown) => {
        const state = {
          comparisonData: null,
          isLoading: false,
          error: 'Incompatible evaluations',
          fetchComparison: mockFetchComparison,
          clearSelection: vi.fn(),
        };
        return selector(state);
      },
    );

    render(<ResultComparison />);
    expect(screen.getByText(/incompatible evaluations/i)).toBeInTheDocument();
  });

  it('renders leaderboard when comparison data is available', () => {
    mockedUseResultStore.mockImplementation(
      (selector: (state: Record<string, unknown>) => unknown) => {
        const state = {
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
          isLoading: false,
          error: null,
          fetchComparison: mockFetchComparison,
          clearSelection: vi.fn(),
        };
        return selector(state);
      },
    );

    render(<ResultComparison />);
    // Should show evaluation names in leaderboard
    expect(screen.getByText('Eval A')).toBeInTheDocument();
    expect(screen.getByText('Eval B')).toBeInTheDocument();
    // Should show the comparison heading
    expect(screen.getByText('Evaluation Comparison')).toBeInTheDocument();
  });

  it('renders per-item comparison grid when items exist', () => {
    mockedUseResultStore.mockImplementation(
      (selector: (state: Record<string, unknown>) => unknown) => {
        const state = {
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
          isLoading: false,
          error: null,
          fetchComparison: mockFetchComparison,
          clearSelection: vi.fn(),
        };
        return selector(state);
      },
    );

    render(<ResultComparison />);
    // Should show the per-item section
    expect(screen.getByText(/per-item comparison/i)).toBeInTheDocument();
    expect(screen.getByText('item-1')).toBeInTheDocument();
  });

  it('renders back button', () => {
    render(<ResultComparison />);
    expect(screen.getByText(/back to results/i)).toBeInTheDocument();
  });
});
