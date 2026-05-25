import { create } from 'zustand';
import type { Dataset } from '@/types';

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
}));
