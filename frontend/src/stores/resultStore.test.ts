import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useResultStore } from './resultStore';

vi.mock('@/services/api', () => ({
  api: {
    listResults: vi.fn(),
    getResult: vi.fn(),
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
          status: 'completed' as const,
          scores: [],
          aggregate_metrics: {
            mean_score: 0.85,
            median_score: 0.9,
            pass_rate: 0.8,
            score_distribution: {},
            total_items: 10,
            passed_items: 8,
            failed_items: 2,
          },
          created_at: '2026-01-01T00:00:00Z',
          completed_at: '2026-01-01T01:00:00Z',
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
        status: 'completed' as const,
        scores: [],
        aggregate_metrics: {
          mean_score: 0.85,
          median_score: 0.9,
          pass_rate: 0.8,
          score_distribution: {},
          total_items: 10,
          passed_items: 8,
          failed_items: 2,
        },
        created_at: '2026-01-01T00:00:00Z',
        completed_at: '2026-01-01T01:00:00Z',
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
});
