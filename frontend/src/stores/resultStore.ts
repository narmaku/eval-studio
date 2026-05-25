import { create } from 'zustand';
import type { Result } from '@/types';

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
}));
