import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useEvaluationRun } from './useEvaluationRun';
import type { CreateEvaluationRequest } from '@/types';

const mockCreateAndRunEvaluation = vi.fn();
const mockSetCurrentEvaluation = vi.fn();
const mockGetRunningEvaluation = vi.fn();
const mockFetchResults = vi.fn();
const mockAddNotification = vi.fn();
const mockResetSelection = vi.fn();
const mockCancelEvaluation = vi.fn();

vi.mock('@/stores/evaluationStore', () => ({
  useEvaluationStore: Object.assign(
    vi.fn(() => ({
      currentEvaluation: null,
      createAndRunEvaluation: mockCreateAndRunEvaluation,
      isLoading: false,
      getRunningEvaluation: mockGetRunningEvaluation,
      setCurrentEvaluation: mockSetCurrentEvaluation,
    })),
    {
      getState: () => ({
        currentEvaluation: null,
      }),
    },
  ),
}));

vi.mock('@/stores/resultStore', () => ({
  useResultStore: vi.fn(() => ({
    fetchResults: mockFetchResults,
  })),
}));

vi.mock('@/stores/notificationStore', () => ({
  useNotificationStore: Object.assign(
    vi.fn(() => ({})),
    {
      getState: () => ({
        addNotification: mockAddNotification,
      }),
    },
  ),
}));

vi.mock('@/stores/evaluatorStore', () => ({
  useEvaluatorStore: Object.assign(
    vi.fn(() => ({})),
    {
      getState: () => ({
        resetSelection: mockResetSelection,
      }),
    },
  ),
}));

vi.mock('@/services/api', () => ({
  api: {
    cancelEvaluation: (...args: unknown[]) => mockCancelEvaluation(...args),
  },
}));

describe('useEvaluationRun', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    mockGetRunningEvaluation.mockReturnValue(null);
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('starts in configure phase by default', () => {
    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));
    expect(result.current.phase).toBe('configure');
  });

  it('resumes to running phase from sessionStorage', () => {
    sessionStorage.setItem(
      'runningEvaluation',
      JSON.stringify({ mode: 'qa', id: 'e1', name: 'Test' }),
    );
    mockGetRunningEvaluation.mockReturnValue({ mode: 'qa', id: 'e1', name: 'Test' });

    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));
    expect(result.current.phase).toBe('running');
    expect(mockSetCurrentEvaluation).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'e1', mode: 'qa' }),
    );
  });

  it('does not resume for a different mode', () => {
    sessionStorage.setItem(
      'runningEvaluation',
      JSON.stringify({ mode: 'rag', id: 'e1', name: 'Test' }),
    );
    mockGetRunningEvaluation.mockReturnValue({ mode: 'rag', id: 'e1', name: 'Test' });

    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));
    expect(result.current.phase).toBe('configure');
    expect(mockSetCurrentEvaluation).not.toHaveBeenCalled();
  });

  it('transitions to running on successful start', async () => {
    mockCreateAndRunEvaluation.mockResolvedValue({});

    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));

    await act(async () => {
      await result.current.start({
        name: 'Test',
        mode: 'qa',
        dataset_id: 'ds-1',
        config: {},
      } as CreateEvaluationRequest);
    });

    expect(result.current.phase).toBe('running');
    expect(mockCreateAndRunEvaluation).toHaveBeenCalledTimes(1);
  });

  it('stays on configure when start fails', async () => {
    mockCreateAndRunEvaluation.mockRejectedValue(new Error('Server error'));

    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));

    await act(async () => {
      await result.current.start({
        name: 'Test',
        mode: 'qa',
        dataset_id: 'ds-1',
        config: {},
      } as CreateEvaluationRequest);
    });

    expect(result.current.phase).toBe('configure');
    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error', title: 'Failed to Start Evaluation' }),
    );
  });

  it('handles completed evaluation', async () => {
    const { useEvaluationStore } = await import('@/stores/evaluationStore');
    Object.assign(useEvaluationStore, {
      getState: () => ({
        currentEvaluation: { id: 'e1', status: 'completed', name: 'Done Eval' },
      }),
    });

    const onCompleted = vi.fn();
    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa', onCompleted }));

    act(() => {
      result.current.handleComplete();
    });

    expect(result.current.phase).toBe('complete');
    expect(mockFetchResults).toHaveBeenCalledWith('e1');
    expect(onCompleted).toHaveBeenCalledWith('e1');
    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'success', title: 'Evaluation Completed' }),
    );
  });

  it('handles failed evaluation', async () => {
    const { useEvaluationStore } = await import('@/stores/evaluationStore');
    Object.assign(useEvaluationStore, {
      getState: () => ({
        currentEvaluation: { id: 'e1', status: 'failed', name: 'Bad Eval', error: 'timeout' },
      }),
    });

    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));

    act(() => {
      result.current.handleComplete();
    });

    expect(result.current.phase).toBe('configure');
    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error', title: 'Evaluation Failed' }),
    );
  });

  it('handles cancelled evaluation', async () => {
    const { useEvaluationStore } = await import('@/stores/evaluationStore');
    Object.assign(useEvaluationStore, {
      getState: () => ({
        currentEvaluation: { id: 'e1', status: 'cancelled', name: 'Cancelled Eval' },
      }),
    });

    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));

    act(() => {
      result.current.handleComplete();
    });

    expect(result.current.phase).toBe('configure');
    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'warning', title: 'Evaluation Cancelled' }),
    );
  });

  it('calls cancelEvaluation API', async () => {
    mockCancelEvaluation.mockResolvedValue({});

    const { useEvaluationStore } = await import('@/stores/evaluationStore');
    (useEvaluationStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      currentEvaluation: { id: 'e1' },
      createAndRunEvaluation: mockCreateAndRunEvaluation,
      isLoading: false,
      getRunningEvaluation: mockGetRunningEvaluation,
      setCurrentEvaluation: mockSetCurrentEvaluation,
    });

    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));

    act(() => {
      result.current.cancel();
    });

    expect(mockCancelEvaluation).toHaveBeenCalledWith('e1');
  });

  it('resets to configure phase and clears evaluator selection', () => {
    const { result } = renderHook(() => useEvaluationRun({ mode: 'qa' }));

    act(() => {
      result.current.reset();
    });

    expect(result.current.phase).toBe('configure');
    expect(mockResetSelection).toHaveBeenCalled();
  });
});
