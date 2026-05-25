import { create } from 'zustand';
import type { Evaluation, CreateEvaluationRequest } from '@/types';
import { api } from '@/services/api';

const POLL_INTERVAL_MS = 2000;

interface EvaluationStore {
  evaluations: Evaluation[];
  currentEvaluation: Evaluation | null;
  isLoading: boolean;
  error: string | null;

  setEvaluations: (evaluations: Evaluation[]) => void;
  setCurrentEvaluation: (evaluation: Evaluation | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchEvaluations: (params?: { mode?: string; status?: string }) => Promise<void>;
  createAndRunEvaluation: (request: CreateEvaluationRequest) => Promise<Evaluation>;
  pollEvaluation: (id: string, onComplete: () => void) => () => void;
}

export const useEvaluationStore = create<EvaluationStore>((set, _get) => ({
  evaluations: [],
  currentEvaluation: null,
  isLoading: false,
  error: null,

  setEvaluations: (evaluations) => set({ evaluations }),
  setCurrentEvaluation: (currentEvaluation) => set({ currentEvaluation }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  fetchEvaluations: async (params?: { mode?: string; status?: string }) => {
    set({ isLoading: true, error: null });
    try {
      const queryParams: { mode?: string; status?: string } = {};
      if (params?.mode) {
        queryParams.mode = params.mode;
      }
      if (params?.status) {
        queryParams.status = params.status;
      }
      const response = await api.listEvaluations(queryParams);
      set({ evaluations: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch evaluations';
      set({ error: message, isLoading: false });
    }
  },

  createAndRunEvaluation: async (request: CreateEvaluationRequest) => {
    set({ isLoading: true, error: null });
    try {
      const evaluation = await api.createEvaluation(request);
      const runningEvaluation = await api.rerunEvaluation(evaluation.id);
      set({ currentEvaluation: runningEvaluation, isLoading: false });
      return runningEvaluation;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create evaluation';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  pollEvaluation: (id: string, onComplete: () => void) => {
    const intervalId = setInterval(async () => {
      try {
        const evaluation = await api.getEvaluation(id);
        set({ currentEvaluation: evaluation });
        if (
          evaluation.status === 'completed' ||
          evaluation.status === 'failed' ||
          evaluation.status === 'cancelled'
        ) {
          clearInterval(intervalId);
          onComplete();
        }
      } catch {
        // Silently ignore polling errors to avoid spamming the user;
        // the next tick will retry. If the evaluation is truly gone,
        // the page will handle it via status checks.
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  },
}));
