import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useResultStore } from './resultStore';

vi.mock('@/services/api', () => ({
  api: {
    listResults: vi.fn(),
    getResult: vi.fn(),
    compareEvaluations: vi.fn(),
  },
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

describe('resultStore', () => {
  beforeEach(() => {
    useResultStore.setState({
      results: [],
      currentResult: null,
      isLoading: false,
      error: null,
      selectedEvaluationIds: [],
      referenceEvaluationId: null,
      comparisonData: null,
    });
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useResultStore.getState();
    expect(state.results).toEqual([]);
    expect(state.currentResult).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('can set and clear error', () => {
    const { setError, clearError } = useResultStore.getState();
    setError('Something went wrong');
    expect(useResultStore.getState().error).toBe('Something went wrong');
    clearError();
    expect(useResultStore.getState().error).toBeNull();
  });

  it('can set loading state', () => {
    const { setLoading } = useResultStore.getState();
    setLoading(true);
    expect(useResultStore.getState().isLoading).toBe(true);
    setLoading(false);
    expect(useResultStore.getState().isLoading).toBe(false);
  });

  describe('fetchResults', () => {
    it('sets loading, stores results, clears loading on success', async () => {
      const mockResults = [
        {
          id: 'r1',
          evaluation_id: 'e1',
          dataset_item_id: 'item-1',
          session_id: null,
          contestant_model: null,
          score: 0.85,
          passed: true,
          actual_answer: 'test answer',
          judge_reasoning: 'good answer',
          scores_breakdown: null,
          retrieved_chunks: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ];
      mockedApi.listResults.mockResolvedValue({
        items: mockResults,
        total: 1,
        page: 1,
        page_size: 20,
        pages: 1,
      });

      const promise = useResultStore.getState().fetchResults();
      expect(useResultStore.getState().isLoading).toBe(true);
      expect(useResultStore.getState().error).toBeNull();

      await promise;

      expect(useResultStore.getState().isLoading).toBe(false);
      expect(useResultStore.getState().results).toEqual(mockResults);
      expect(mockedApi.listResults).toHaveBeenCalledWith({});
    });

    it('passes evaluationId filter when provided', async () => {
      mockedApi.listResults.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        pages: 0,
      });

      await useResultStore.getState().fetchResults('eval-123');

      expect(mockedApi.listResults).toHaveBeenCalledWith({ evaluation_id: 'eval-123' });
    });

    it('handles API error: sets error string', async () => {
      mockedApi.listResults.mockRejectedValue(new Error('Network error'));

      await useResultStore.getState().fetchResults();

      expect(useResultStore.getState().isLoading).toBe(false);
      expect(useResultStore.getState().error).toBe('Network error');
      expect(useResultStore.getState().results).toEqual([]);
    });
  });

  describe('fetchResult', () => {
    it('stores single result in currentResult', async () => {
      const mockResult = {
        id: 'r1',
        evaluation_id: 'e1',
        dataset_item_id: 'item-1',
        session_id: null,
        contestant_model: null,
        score: 0.85,
        passed: true,
        actual_answer: 'test answer',
        judge_reasoning: 'good answer',
        scores_breakdown: null,
        retrieved_chunks: null,
        created_at: '2026-01-01T00:00:00Z',
      };
      mockedApi.getResult.mockResolvedValue(mockResult);

      const promise = useResultStore.getState().fetchResult('r1');
      expect(useResultStore.getState().isLoading).toBe(true);

      await promise;

      expect(useResultStore.getState().isLoading).toBe(false);
      expect(useResultStore.getState().currentResult).toEqual(mockResult);
      expect(mockedApi.getResult).toHaveBeenCalledWith('r1');
    });

    it('handles API error when fetching single result', async () => {
      mockedApi.getResult.mockRejectedValue(new Error('Not found'));

      await useResultStore.getState().fetchResult('nonexistent');

      expect(useResultStore.getState().isLoading).toBe(false);
      expect(useResultStore.getState().error).toBe('Not found');
      expect(useResultStore.getState().currentResult).toBeNull();
    });
  });

  describe('selection state', () => {
    it('has correct initial selection state', () => {
      const state = useResultStore.getState();
      expect(state.selectedEvaluationIds).toEqual([]);
      expect(state.referenceEvaluationId).toBeNull();
      expect(state.comparisonData).toBeNull();
    });

    it('toggleSelection adds an evaluation id', () => {
      useResultStore.getState().toggleSelection('e1');
      expect(useResultStore.getState().selectedEvaluationIds).toEqual(['e1']);
    });

    it('toggleSelection removes an already-selected id', () => {
      useResultStore.setState({ selectedEvaluationIds: ['e1', 'e2'] });
      useResultStore.getState().toggleSelection('e1');
      expect(useResultStore.getState().selectedEvaluationIds).toEqual(['e2']);
    });

    it('toggleSelection sets reference to first selected when adding', () => {
      useResultStore.getState().toggleSelection('e1');
      expect(useResultStore.getState().referenceEvaluationId).toBe('e1');
    });

    it('toggleSelection clears reference when removing the reference id', () => {
      useResultStore.setState({
        selectedEvaluationIds: ['e1', 'e2'],
        referenceEvaluationId: 'e1',
      });
      useResultStore.getState().toggleSelection('e1');
      expect(useResultStore.getState().referenceEvaluationId).toBe('e2');
    });

    it('setReference updates the reference evaluation', () => {
      useResultStore.setState({ selectedEvaluationIds: ['e1', 'e2'] });
      useResultStore.getState().setReference('e2');
      expect(useResultStore.getState().referenceEvaluationId).toBe('e2');
    });

    it('clearSelection resets all selection state', () => {
      useResultStore.setState({
        selectedEvaluationIds: ['e1', 'e2'],
        referenceEvaluationId: 'e1',
        comparisonData: {
          evaluations: [],
          item_comparisons: [],
          reference_evaluation_id: null,
        },
      });
      useResultStore.getState().clearSelection();
      expect(useResultStore.getState().selectedEvaluationIds).toEqual([]);
      expect(useResultStore.getState().referenceEvaluationId).toBeNull();
      expect(useResultStore.getState().comparisonData).toBeNull();
    });
  });

  describe('fetchComparison', () => {
    it('fetches comparison data and stores it', async () => {
      const mockComparison = {
        evaluations: [
          {
            evaluation_id: 'e1',
            evaluation_name: 'Eval A',
            total_items: 5,
            passed_count: 4,
            failed_count: 1,
            average_score: 0.85,
            min_score: 0.5,
            max_score: 1.0,
            results: [],
          },
        ],
        item_comparisons: [],
        reference_evaluation_id: 'e1',
      };
      mockedApi.compareEvaluations.mockResolvedValue(mockComparison);

      await useResultStore.getState().fetchComparison(['e1', 'e2'], 'e1');

      expect(useResultStore.getState().comparisonData).toEqual(mockComparison);
      expect(useResultStore.getState().isLoading).toBe(false);
      expect(mockedApi.compareEvaluations).toHaveBeenCalledWith(['e1', 'e2'], 'e1');
    });

    it('handles comparison API error', async () => {
      mockedApi.compareEvaluations.mockRejectedValue(new Error('Incompatible'));

      await useResultStore.getState().fetchComparison(['e1', 'e2']);

      expect(useResultStore.getState().isLoading).toBe(false);
      expect(useResultStore.getState().error).toBe('Incompatible');
      expect(useResultStore.getState().comparisonData).toBeNull();
    });
  });
});
