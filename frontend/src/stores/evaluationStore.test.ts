import { describe, it, expect } from 'vitest';
import { useEvaluationStore } from './evaluationStore';

describe('evaluationStore', () => {
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
});
