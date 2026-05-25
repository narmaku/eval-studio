import { create } from 'zustand';
import type { Evaluation } from '@/types';
import { api } from '@/services/api';

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
}

export const useEvaluationStore = create<EvaluationStore>((set) => ({
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
}));
