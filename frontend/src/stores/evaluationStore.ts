import { create } from 'zustand';
import type { Evaluation } from '@/types';

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
}));
