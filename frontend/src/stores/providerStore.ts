import { create } from 'zustand';
import type { Provider, CreateProviderRequest, UpdateProviderRequest } from '@/types';
import { api } from '@/services/api';

interface ProviderStore {
  providers: Provider[];
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchProviders: (purpose?: string) => Promise<void>;
  createProvider: (data: CreateProviderRequest) => Promise<Provider>;
  updateProvider: (id: string, data: UpdateProviderRequest) => Promise<Provider>;
  deleteProvider: (id: string) => Promise<void>;
}

export const useProviderStore = create<ProviderStore>((set) => ({
  providers: [],
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchProviders: async (purpose?: string) => {
    set({ isLoading: true, error: null });
    try {
      const providers = await api.listProviders(purpose);
      set({ providers, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch providers';
      set({ error: message, isLoading: false });
    }
  },

  createProvider: async (data: CreateProviderRequest) => {
    set({ error: null });
    try {
      const provider = await api.createProvider(data);
      set((state) => ({ providers: [...state.providers, provider] }));
      return provider;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create provider';
      set({ error: message });
      throw err;
    }
  },

  updateProvider: async (id: string, data: UpdateProviderRequest) => {
    set({ error: null });
    try {
      const updated = await api.updateProvider(id, data);
      set((state) => ({
        providers: state.providers.map((p) => (p.id === id ? updated : p)),
      }));
      return updated;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update provider';
      set({ error: message });
      throw err;
    }
  },

  deleteProvider: async (id: string) => {
    set({ error: null });
    try {
      await api.deleteProvider(id);
      set((state) => ({
        providers: state.providers.filter((p) => p.id !== id),
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete provider';
      set({ error: message });
      throw err;
    }
  },
}));
