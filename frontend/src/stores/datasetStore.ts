import { create } from 'zustand';
import type { Dataset } from '@/types';
import { api } from '@/services/api';

interface DatasetStore {
  datasets: Dataset[];
  currentDataset: Dataset | null;
  isLoading: boolean;
  error: string | null;

  setDatasets: (datasets: Dataset[]) => void;
  setCurrentDataset: (dataset: Dataset | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchDatasets: () => Promise<void>;
}

export const useDatasetStore = create<DatasetStore>((set) => ({
  datasets: [],
  currentDataset: null,
  isLoading: false,
  error: null,

  setDatasets: (datasets) => set({ datasets }),
  setCurrentDataset: (currentDataset) => set({ currentDataset }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  fetchDatasets: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.listDatasets();
      set({ datasets: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch datasets';
      set({ error: message, isLoading: false });
    }
  },
}));
