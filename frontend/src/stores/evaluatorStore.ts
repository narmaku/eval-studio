import { create } from 'zustand';
import type { EvaluatorInfo } from '@/types';
import { api } from '@/services/api';

interface EvaluatorStore {
  evaluators: EvaluatorInfo[];
  selectedEvaluatorId: string | null;
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchEvaluators: (mode?: string) => Promise<void>;
  selectEvaluator: (id: string) => void;
  resetSelection: () => void;
}

export const useEvaluatorStore = create<EvaluatorStore>((set, get) => ({
  evaluators: [],
  selectedEvaluatorId: null,
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchEvaluators: async (mode?: string) => {
    set({ isLoading: true, error: null });
    try {
      const evaluators = await api.listEvaluators(mode);
      const { selectedEvaluatorId } = get();

      // Auto-select first available evaluator if none is currently selected
      let autoSelectedId = selectedEvaluatorId;
      if (!selectedEvaluatorId) {
        const firstAvailable = evaluators.find((e) => e.available);
        autoSelectedId = firstAvailable?.id ?? null;
      }

      set({
        evaluators,
        selectedEvaluatorId: autoSelectedId,
        isLoading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch evaluators';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  selectEvaluator: (id: string) => {
    set({ selectedEvaluatorId: id });
  },

  resetSelection: () => {
    set({ selectedEvaluatorId: null });
  },
}));
