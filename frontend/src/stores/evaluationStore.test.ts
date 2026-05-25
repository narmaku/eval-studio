import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useEvaluationStore } from './evaluationStore';

vi.mock('@/services/api', () => ({
  api: {
    listEvaluations: vi.fn(),
  },
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

describe('evaluationStore', () => {
  beforeEach(() => {
    useEvaluationStore.setState({
      evaluations: [],
      currentEvaluation: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useEvaluationStore.getState();
    expect(state.evaluations).toEqual([]);
    expect(state.currentEvaluation).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('can set and clear error', () => {
    const { setError, clearError } = useEvaluationStore.getState();
    setError('Something went wrong');
    expect(useEvaluationStore.getState().error).toBe('Something went wrong');
    clearError();
    expect(useEvaluationStore.getState().error).toBeNull();
  });

  it('can set loading state', () => {
    const { setLoading } = useEvaluationStore.getState();
    setLoading(true);
    expect(useEvaluationStore.getState().isLoading).toBe(true);
    setLoading(false);
    expect(useEvaluationStore.getState().isLoading).toBe(false);
  });

  describe('fetchEvaluations', () => {
    it('sets loading, stores evaluations, clears loading on success', async () => {
      const mockEvaluations = [
        {
          id: 'e1',
          name: 'Test Eval',
          description: 'A test evaluation',
          mode: 'qa' as const,
          status: 'completed' as const,
          dataset_id: 'd1',
          judge_id: 'j1',
          config: {
            model_endpoint: { name: 'test', litellm_model: 'gpt-4' },
            judge_config: { preset: 'default' },
          },
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T01:00:00Z',
          completed_at: '2026-01-01T01:00:00Z',
          error: null,
        },
      ];
      mockedApi.listEvaluations.mockResolvedValue({
        items: mockEvaluations,
        total: 1,
        page: 1,
        page_size: 20,
        pages: 1,
      });

      const promise = useEvaluationStore.getState().fetchEvaluations();
      expect(useEvaluationStore.getState().isLoading).toBe(true);
      expect(useEvaluationStore.getState().error).toBeNull();

      await promise;

      expect(useEvaluationStore.getState().isLoading).toBe(false);
      expect(useEvaluationStore.getState().evaluations).toEqual(mockEvaluations);
      expect(mockedApi.listEvaluations).toHaveBeenCalledWith({});
    });

    it('passes mode and status filters when provided', async () => {
      mockedApi.listEvaluations.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        pages: 0,
      });

      await useEvaluationStore.getState().fetchEvaluations({ mode: 'qa', status: 'completed' });

      expect(mockedApi.listEvaluations).toHaveBeenCalledWith({ mode: 'qa', status: 'completed' });
    });

    it('handles API error: sets error string', async () => {
      mockedApi.listEvaluations.mockRejectedValue(new Error('Network error'));

      await useEvaluationStore.getState().fetchEvaluations();

      expect(useEvaluationStore.getState().isLoading).toBe(false);
      expect(useEvaluationStore.getState().error).toBe('Network error');
      expect(useEvaluationStore.getState().evaluations).toEqual([]);
    });
  });
});
