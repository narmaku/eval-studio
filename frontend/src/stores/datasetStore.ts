import { create } from 'zustand';
import type {
  Dataset,
  DatasetDetail,
  CreateDatasetRequest,
  AnalyzeResponse,
  ImportRequest,
} from '@/types';
import { api } from '@/services/api';

interface DatasetStore {
  datasets: Dataset[];
  currentDataset: DatasetDetail | null;
  isLoading: boolean;
  error: string | null;

  // Smart import state
  analysisResult: AnalyzeResponse | null;
  isAnalyzing: boolean;
  isImporting: boolean;

  setDatasets: (datasets: Dataset[]) => void;
  setCurrentDataset: (dataset: DatasetDetail | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchDatasets: () => Promise<void>;
  fetchDataset: (id: string) => Promise<void>;
  uploadDataset: (data: CreateDatasetRequest) => Promise<Dataset>;
  removeDataset: (id: string) => Promise<void>;

  // Smart import actions
  analyzeFiles: (files: File[]) => Promise<void>;
  smartImport: (data: ImportRequest) => Promise<Dataset>;
  clearAnalysis: () => void;
}

export const useDatasetStore = create<DatasetStore>((set, get) => ({
  datasets: [],
  currentDataset: null,
  isLoading: false,
  error: null,

  // Smart import initial state
  analysisResult: null,
  isAnalyzing: false,
  isImporting: false,

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

  analyzeFiles: async (files: File[]) => {
    set({ isAnalyzing: true, error: null });
    try {
      const result = await api.analyzeDatasetFiles(files);
      set({ analysisResult: result, isAnalyzing: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to analyze files';
      set({ error: message, isAnalyzing: false });
      throw err;
    }
  },

  smartImport: async (data: ImportRequest) => {
    set({ isImporting: true, error: null });
    try {
      const dataset = await api.importDataset(data);
      set({
        datasets: [dataset, ...get().datasets],
        analysisResult: null,
        isImporting: false,
      });
      return dataset;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to import dataset';
      set({ error: message, isImporting: false });
      throw err;
    }
  },

  clearAnalysis: () => set({ analysisResult: null, isAnalyzing: false }),
}));
