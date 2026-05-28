import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useEvaluatorStore } from './evaluatorStore';
import type { EvaluatorInfo } from '@/types';

vi.mock('@/services/api', () => ({
  api: {
    listEvaluators: vi.fn(),
    getEvaluator: vi.fn(),
  },
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

const makeEvaluator = (overrides: Partial<EvaluatorInfo> = {}): EvaluatorInfo => ({
  id: 'litellm-judge',
  name: 'LLM-as-Judge (LiteLLM)',
  description: 'Direct LLM-as-judge scoring via LiteLLM.',
  modes: ['qa', 'agent', 'rag'],
  builtin: true,
  available: true,
  defaults: { pass_threshold: 0.7, temperature: 0.0 },
  config_schema: { type: 'object', properties: {} },
  ...overrides,
});

describe('evaluatorStore', () => {
  beforeEach(() => {
    useEvaluatorStore.setState({
      evaluators: [],
      selectedEvaluatorId: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useEvaluatorStore.getState();
    expect(state.evaluators).toEqual([]);
    expect(state.selectedEvaluatorId).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  describe('fetchEvaluators', () => {
    it('populates evaluators from API response', async () => {
      const evaluators = [
        makeEvaluator({ id: 'litellm-judge' }),
        makeEvaluator({ id: 'deepeval', name: 'DeepEval', available: false }),
      ];
      mockedApi.listEvaluators.mockResolvedValue(evaluators);

      await useEvaluatorStore.getState().fetchEvaluators();

      const state = useEvaluatorStore.getState();
      expect(state.evaluators).toEqual(evaluators);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('passes mode parameter to API', async () => {
      mockedApi.listEvaluators.mockResolvedValue([]);

      await useEvaluatorStore.getState().fetchEvaluators('qa');

      expect(mockedApi.listEvaluators).toHaveBeenCalledWith('qa');
    });

    it('auto-selects first available evaluator when none is selected', async () => {
      const evaluators = [
        makeEvaluator({ id: 'unavailable', available: false }),
        makeEvaluator({ id: 'litellm-judge', available: true }),
        makeEvaluator({ id: 'another', available: true }),
      ];
      mockedApi.listEvaluators.mockResolvedValue(evaluators);

      await useEvaluatorStore.getState().fetchEvaluators();

      expect(useEvaluatorStore.getState().selectedEvaluatorId).toBe('litellm-judge');
    });

    it('does not change selection if an evaluator is already selected', async () => {
      useEvaluatorStore.setState({ selectedEvaluatorId: 'existing-choice' });
      const evaluators = [makeEvaluator({ id: 'litellm-judge' })];
      mockedApi.listEvaluators.mockResolvedValue(evaluators);

      await useEvaluatorStore.getState().fetchEvaluators();

      expect(useEvaluatorStore.getState().selectedEvaluatorId).toBe('existing-choice');
    });

    it('sets error on API failure', async () => {
      mockedApi.listEvaluators.mockRejectedValue(new Error('Network error'));

      await useEvaluatorStore.getState().fetchEvaluators();

      const state = useEvaluatorStore.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });

    it('sets loading state during fetch', async () => {
      let resolvePromise: (value: EvaluatorInfo[]) => void;
      mockedApi.listEvaluators.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        }),
      );

      const fetchPromise = useEvaluatorStore.getState().fetchEvaluators();
      expect(useEvaluatorStore.getState().isLoading).toBe(true);

      resolvePromise!([]);
      await fetchPromise;
      expect(useEvaluatorStore.getState().isLoading).toBe(false);
    });
  });

  describe('selectEvaluator', () => {
    it('updates selectedEvaluatorId', () => {
      useEvaluatorStore.getState().selectEvaluator('litellm-judge');
      expect(useEvaluatorStore.getState().selectedEvaluatorId).toBe('litellm-judge');
    });

    it('overwrites previous selection', () => {
      useEvaluatorStore.setState({ selectedEvaluatorId: 'old' });
      useEvaluatorStore.getState().selectEvaluator('new');
      expect(useEvaluatorStore.getState().selectedEvaluatorId).toBe('new');
    });
  });

  describe('resetSelection', () => {
    it('clears selectedEvaluatorId to null', () => {
      useEvaluatorStore.setState({ selectedEvaluatorId: 'litellm-judge' });
      useEvaluatorStore.getState().resetSelection();
      expect(useEvaluatorStore.getState().selectedEvaluatorId).toBeNull();
    });
  });
});
