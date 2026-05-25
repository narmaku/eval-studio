import { create } from 'zustand';
import type { Result } from '@/types';
import { api } from '@/services/api';

interface ResultStore {
  results: Result[];
  currentResult: Result | null;
  isLoading: boolean;
  error: string | null;

  setResults: (results: Result[]) => void;
  setCurrentResult: (result: Result | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchResults: (evaluationId: string) => Promise<void>;
}

export const useResultStore = create<ResultStore>((set) => ({
  results: [],
  currentResult: null,
  isLoading: false,
  error: null,

  setResults: (results) => set({ results }),
  setCurrentResult: (currentResult) => set({ currentResult }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  fetchResults: async (evaluationId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.listResults({ evaluation_id: evaluationId });
      set({ results: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch results';
      set({ error: message, isLoading: false });
    }
  },
}));
