import { create } from 'zustand';
import type { Result, UpdateResultRequest, AggregateMetrics, ComparisonResponse } from '@/types';
import { api } from '@/services/api';

interface PaginationState {
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface ResultStore {
  results: Result[];
  currentResult: Result | null;
  isLoading: boolean;
  error: string | null;
  pagination: PaginationState | null;
  aggregateMetrics: AggregateMetrics | null;

  // Selection state for multi-select comparison
  selectedEvaluationIds: string[];
  referenceEvaluationId: string | null;
  comparisonData: ComparisonResponse | null;

  setResults: (results: Result[]) => void;
  setCurrentResult: (result: Result | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchResults: (evaluationId: string, page?: number, pageSize?: number) => Promise<void>;
  fetchResult: (id: string) => Promise<void>;
  updateResult: (id: string, data: UpdateResultRequest) => Promise<Result>;
  deleteResult: (id: string) => Promise<void>;
  fetchAggregateMetrics: (evaluationId: string) => Promise<void>;
  fetchAllResultsForExport: (evaluationId: string) => Promise<Result[]>;

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
  pagination: null,
  aggregateMetrics: null,
  selectedEvaluationIds: [],
  referenceEvaluationId: null,
  comparisonData: null,

  setResults: (results) => set({ results }),
  setCurrentResult: (currentResult) => set({ currentResult }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  fetchResults: async (evaluationId: string, page = 1, pageSize = 20) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.listResults({
        evaluation_id: evaluationId,
        page,
        page_size: pageSize,
      });
      set({
        results: response.items,
        pagination: {
          total: response.total,
          page: response.page,
          page_size: response.page_size,
          pages: response.pages,
        },
        isLoading: false,
      });
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

  updateResult: async (id: string, data: UpdateResultRequest) => {
    set({ error: null });
    try {
      const updated = await api.updateResult(id, data);
      set((state) => ({
        results: state.results.map((r) => (r.id === id ? updated : r)),
        currentResult: state.currentResult?.id === id ? updated : state.currentResult,
      }));
      return updated;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update result';
      set({ error: message });
      throw err;
    }
  },

  deleteResult: async (id: string) => {
    set({ error: null });
    try {
      await api.deleteResult(id);
      set((state) => ({
        results: state.results.filter((r) => r.id !== id),
        currentResult: state.currentResult?.id === id ? null : state.currentResult,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete result';
      set({ error: message });
      throw err;
    }
  },

  fetchAggregateMetrics: async (evaluationId: string) => {
    try {
      const metrics = await api.getAggregateMetrics(evaluationId);
      set({ aggregateMetrics: metrics });
    } catch {
      // Don't block on this -- set null
      set({ aggregateMetrics: null });
    }
  },

  fetchAllResultsForExport: async (evaluationId: string): Promise<Result[]> => {
    const allResults: Result[] = [];
    let page = 1;
    const pageSize = 500; // larger pages for export
    while (true) {
      const response = await api.listResults({
        evaluation_id: evaluationId,
        page,
        page_size: pageSize,
      });
      allResults.push(...response.items);
      if (page >= response.pages) break;
      page++;
    }
    return allResults;
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
