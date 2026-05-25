import { create } from 'zustand';
import type { Dataset, DatasetDetail, CreateDatasetRequest } from '@/types';
import { api } from '@/services/api';

interface DatasetStore {
  datasets: Dataset[];
  currentDataset: DatasetDetail | null;
  isLoading: boolean;
  error: string | null;

  setDatasets: (datasets: Dataset[]) => void;
  setCurrentDataset: (dataset: DatasetDetail | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchDatasets: () => Promise<void>;
  fetchDataset: (id: string) => Promise<void>;
  uploadDataset: (data: CreateDatasetRequest) => Promise<Dataset>;
  removeDataset: (id: string) => Promise<void>;
}

export const useDatasetStore = create<DatasetStore>((set, get) => ({
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

  fetchDataset: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const detail = await api.getDataset(id);
      set({ currentDataset: detail, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch dataset';
      set({ error: message, isLoading: false });
    }
  },

  uploadDataset: async (data: CreateDatasetRequest) => {
    try {
      const dataset = await api.createDataset(data);
      set({ datasets: [dataset, ...get().datasets] });
      return dataset;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to upload dataset';
      set({ error: message });
      throw err;
    }
  },

  removeDataset: async (id: string) => {
    try {
      await api.deleteDataset(id);
      const { currentDataset } = get();
      set({
        datasets: get().datasets.filter((d) => d.id !== id),
        currentDataset: currentDataset?.id === id ? null : currentDataset,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete dataset';
      set({ error: message });
      throw err;
    }
  },
}));
