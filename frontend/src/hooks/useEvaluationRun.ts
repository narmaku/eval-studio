import { useState, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import { useResultStore } from '@/stores/resultStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { api } from '@/services/api';
import type { CreateEvaluationRequest, EvaluationMode } from '@/types';

export type PagePhase = 'configure' | 'running' | 'complete';

function getInitialPhase(mode: EvaluationMode): PagePhase {
  try {
    const stored = sessionStorage.getItem('runningEvaluation');
    if (stored) {
      const running = JSON.parse(stored) as { mode: string };
      if (running.mode === mode) return 'running';
    }
  } catch {
    // ignore
  }
  return 'configure';
}

interface UseEvaluationRunOptions {
  mode: EvaluationMode;
  onCompleted?: (evaluationId: string) => void;
}

export function useEvaluationRun({ mode, onCompleted }: UseEvaluationRunOptions) {
  const [phase, setPhase] = useState<PagePhase>(() => getInitialPhase(mode));

  const {
    currentEvaluation,
    createAndRunEvaluation,
    isLoading,
    getRunningEvaluation,
    setCurrentEvaluation,
  } = useEvaluationStore();
  const { fetchResults } = useResultStore();

  useEffect(() => {
    const running = getRunningEvaluation();
    if (running && running.mode === mode) {
      setCurrentEvaluation({
        id: running.id,
        name: running.name,
        mode: running.mode,
      } as Parameters<typeof setCurrentEvaluation>[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const start = useCallback(
    async (request: CreateEvaluationRequest) => {
      try {
        await createAndRunEvaluation(request);
        toast.success('Evaluation started');
        setPhase('running');
      } catch (err) {
        toast.error('Failed to start evaluation');
        useNotificationStore.getState().addNotification({
          type: 'error',
          title: 'Failed to Start Evaluation',
          message: err instanceof Error ? err.message : 'An unknown error occurred',
          details: err instanceof Error ? err.stack : undefined,
        });
      }
    },
    [createAndRunEvaluation],
  );

  const handleComplete = useCallback(() => {
    const evaluation = useEvaluationStore.getState().currentEvaluation;
    const addNotification = useNotificationStore.getState().addNotification;

    if (evaluation?.status === 'completed') {
      toast.success('Evaluation completed');
      addNotification({
        type: 'success',
        title: 'Evaluation Completed',
        message: `"${evaluation.name}" finished successfully`,
        evaluationId: evaluation.id,
      });
      void fetchResults(evaluation.id);
      onCompleted?.(evaluation.id);
      setPhase('complete');
    } else if (evaluation?.status === 'failed') {
      const errorMsg = evaluation.error || 'Unknown error';
      toast.error(`Evaluation failed: ${errorMsg}`);
      addNotification({
        type: 'error',
        title: 'Evaluation Failed',
        message: `"${evaluation.name}" failed: ${errorMsg}`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    } else if (evaluation?.status === 'cancelled') {
      toast('Evaluation was cancelled');
      addNotification({
        type: 'warning',
        title: 'Evaluation Cancelled',
        message: `"${evaluation.name}" was cancelled`,
        evaluationId: evaluation.id,
      });
      setPhase('configure');
    }
  }, [fetchResults, onCompleted]);

  const cancel = useCallback(() => {
    if (currentEvaluation?.id) {
      api.cancelEvaluation(currentEvaluation.id).catch(() => {
        toast.error('Failed to cancel evaluation');
      });
    }
  }, [currentEvaluation]);

  const reset = useCallback(() => {
    setPhase('configure');
    useEvaluatorStore.getState().resetSelection();
  }, []);

  return { phase, currentEvaluation, isLoading, start, handleComplete, cancel, reset };
}
