import { create } from 'zustand';
import type { Result, ComparisonResponse } from '@/types';
import { api } from '@/services/api';

interface ResultStore {
  results: Result[];
  currentResult: Result | null;
  isLoading: boolean;
  error: string | null;

  // Selection state for multi-select comparison
  selectedEvaluationIds: string[];
  referenceEvaluationId: string | null;
  comparisonData: ComparisonResponse | null;

  setResults: (results: Result[]) => void;
  setCurrentResult: (result: Result | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchResults: (evaluationId?: string) => Promise<void>;
  fetchResult: (id: string) => Promise<void>;

  // Selection actions
  toggleSelection: (evaluationId: string) => void;
  setReference: (evaluationId: string) => void;
  clearSelection: () => void;
  fetchComparison: (evaluationIds: string[], referenceId?: string) => Promise<void>;
}

export const useResultStore = create<ResultStore>((set, get) => ({
  results: [],
  currentResult: null,
  isLoading: false,
  error: null,
  selectedEvaluationIds: [],
  referenceEvaluationId: null,
  comparisonData: null,

  setResults: (results) => set({ results }),
  setCurrentResult: (currentResult) => set({ currentResult }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  fetchResults: async (evaluationId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const params: { evaluation_id?: string; page_size?: number } = {};
      if (evaluationId) {
        params.evaluation_id = evaluationId;
        params.page_size = 10000;
      }
      const response = await api.listResults(params);
      set({ results: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch results';
      set({ error: message, isLoading: false });
    }
  },

  fetchResult: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await api.getResult(id);
      set({ currentResult: result, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch result';
      set({ error: message, isLoading: false });
    }
  },

  toggleSelection: (evaluationId: string) => {
    const { selectedEvaluationIds, referenceEvaluationId } = get();
    const isSelected = selectedEvaluationIds.includes(evaluationId);

    if (isSelected) {
      const newSelected = selectedEvaluationIds.filter((id) => id !== evaluationId);
      const newReference =
        referenceEvaluationId === evaluationId ? (newSelected[0] ?? null) : referenceEvaluationId;
      set({
        selectedEvaluationIds: newSelected,
        referenceEvaluationId: newReference,
      });
    } else {
      const newSelected = [...selectedEvaluationIds, evaluationId];
      set({
        selectedEvaluationIds: newSelected,
        referenceEvaluationId: referenceEvaluationId ?? evaluationId,
      });
    }
  },

  setReference: (evaluationId: string) => {
    set({ referenceEvaluationId: evaluationId });
  },

  clearSelection: () => {
    set({
      selectedEvaluationIds: [],
      referenceEvaluationId: null,
      comparisonData: null,
    });
  },

  fetchComparison: async (evaluationIds: string[], referenceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.compareEvaluations(evaluationIds, referenceId);
      set({ comparisonData: data, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch comparison';
      set({ error: message, isLoading: false });
    }
  },
}));
