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
    const rubric = await api.createRubric(data);
    set((state) => ({ rubrics: [...state.rubrics, rubric] }));
    return rubric;
  },

  updateRubric: async (id: string, data: UpdateRubricRequest) => {
    const updated = await api.updateRubric(id, data);
    set((state) => ({
      rubrics: state.rubrics.map((r) => (r.id === id ? updated : r)),
    }));
    return updated;
  },

  deleteRubric: async (id: string) => {
    await api.deleteRubric(id);
    set((state) => ({
      rubrics: state.rubrics.filter((r) => r.id !== id),
    }));
  },

  importRubric: async (data: ImportRubricRequest) => {
    const rubric = await api.importRubric(data);
    set((state) => ({ rubrics: [...state.rubrics, rubric] }));
    return rubric;
  },

  generateRubric: async (data: GenerateRubricRequest) => {
    const rubric = await api.generateRubric(data);
    set((state) => ({ rubrics: [...state.rubrics, rubric] }));
    return rubric;
  },

  refineRubric: async (id: string, data: RefineRubricRequest) => {
    const updated = await api.refineRubric(id, data);
    set((state) => ({
      rubrics: state.rubrics.map((r) => (r.id === id ? updated : r)),
    }));
    return updated;
  },
}));
