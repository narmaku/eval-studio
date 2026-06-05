import { create } from 'zustand';
import type { Harness } from '@/types';
import { api } from '@/services/api';

interface HarnessStore {
  harnesses: Harness[];
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchHarnesses: (params?: { type?: string; enabled?: boolean }) => Promise<void>;
  checkHarness: (id: string) => Promise<{ available: boolean; version: string | null }>;
}

export const useHarnessStore = create<HarnessStore>((set) => ({
  harnesses: [],
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchHarnesses: async (params?: { type?: string; enabled?: boolean }) => {
    set({ isLoading: true, error: null });
    try {
      const harnesses = await api.listHarnesses(params);
      set({ harnesses, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch harnesses';
      set({ error: message, isLoading: false });
    }
  },

  checkHarness: async (id: string) => {
    return api.checkHarness(id);
  },
}));
