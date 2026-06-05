import { create } from 'zustand';
import type {
  Rubric,
  CreateRubricRequest,
  UpdateRubricRequest,
  ImportRubricRequest,
  GenerateRubricRequest,
  RefineRubricRequest,
} from '@/types';
import { api } from '@/services/api';

interface RubricStore {
  rubrics: Rubric[];
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchRubrics: (nameFilter?: string) => Promise<void>;
  createRubric: (data: CreateRubricRequest) => Promise<Rubric>;
  updateRubric: (id: string, data: UpdateRubricRequest) => Promise<Rubric>;
  deleteRubric: (id: string) => Promise<void>;
  importRubric: (data: ImportRubricRequest) => Promise<Rubric>;
  generateRubric: (data: GenerateRubricRequest) => Promise<Rubric>;
  refineRubric: (id: string, data: RefineRubricRequest) => Promise<Rubric>;
}

export const useRubricStore = create<RubricStore>((set) => ({
  rubrics: [],
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchRubrics: async (nameFilter?: string) => {
    set({ isLoading: true, error: null });
    try {
      const params: { name?: string } = {};
      if (nameFilter) {
        params.name = nameFilter;
      }
      const response = await api.listRubrics(params);
      set({ rubrics: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch rubrics';
      set({ error: message, isLoading: false });
    }
  },

  createRubric: async (data: CreateRubricRequest) => {
    set({ error: null });
    try {
      const rubric = await api.createRubric(data);
      set((state) => ({ rubrics: [...state.rubrics, rubric] }));
      return rubric;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create rubric';
      set({ error: message });
      throw err;
    }
  },

  updateRubric: async (id: string, data: UpdateRubricRequest) => {
    set({ error: null });
    try {
      const updated = await api.updateRubric(id, data);
      set((state) => ({
        rubrics: state.rubrics.map((r) => (r.id === id ? updated : r)),
      }));
      return updated;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update rubric';
      set({ error: message });
      throw err;
    }
  },

  deleteRubric: async (id: string) => {
    set({ error: null });
    try {
      await api.deleteRubric(id);
      set((state) => ({
        rubrics: state.rubrics.filter((r) => r.id !== id),
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete rubric';
      set({ error: message });
      throw err;
    }
  },

  importRubric: async (data: ImportRubricRequest) => {
    set({ error: null });
    try {
      const rubric = await api.importRubric(data);
      set((state) => ({ rubrics: [...state.rubrics, rubric] }));
      return rubric;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to import rubric';
      set({ error: message });
      throw err;
    }
  },

  generateRubric: async (data: GenerateRubricRequest) => {
    set({ error: null });
    try {
      const rubric = await api.generateRubric(data);
      set((state) => ({ rubrics: [...state.rubrics, rubric] }));
      return rubric;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate rubric';
      set({ error: message });
      throw err;
    }
  },

  refineRubric: async (id: string, data: RefineRubricRequest) => {
    set({ error: null });
    try {
      const updated = await api.refineRubric(id, data);
      set((state) => ({
        rubrics: state.rubrics.map((r) => (r.id === id ? updated : r)),
      }));
      return updated;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to refine rubric';
      set({ error: message });
      throw err;
    }
  },
}));
