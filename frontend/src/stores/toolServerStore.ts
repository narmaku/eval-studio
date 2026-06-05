import { create } from 'zustand';
import type { ToolServer, CreateToolServerRequest, UpdateToolServerRequest } from '@/types';
import { api } from '@/services/api';

interface ToolServerStore {
  toolServers: ToolServer[];
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchToolServers: (params?: { type?: string; enabled?: boolean }) => Promise<void>;
  createToolServer: (data: CreateToolServerRequest) => Promise<ToolServer>;
  updateToolServer: (id: string, data: UpdateToolServerRequest) => Promise<ToolServer>;
  deleteToolServer: (id: string) => Promise<void>;
}

export const useToolServerStore = create<ToolServerStore>((set) => ({
  toolServers: [],
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchToolServers: async (params?: { type?: string; enabled?: boolean }) => {
    set({ isLoading: true, error: null });
    try {
      const toolServers = await api.listToolServers(params);
      set({ toolServers, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch tool servers';
      set({ error: message, isLoading: false });
    }
  },

  createToolServer: async (data: CreateToolServerRequest) => {
    set({ error: null });
    try {
      const toolServer = await api.createToolServer(data);
      set((state) => ({ toolServers: [...state.toolServers, toolServer] }));
      return toolServer;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create tool server';
      set({ error: message });
      throw err;
    }
  },

  updateToolServer: async (id: string, data: UpdateToolServerRequest) => {
    set({ error: null });
    try {
      const updated = await api.updateToolServer(id, data);
      set((state) => ({
        toolServers: state.toolServers.map((s) => (s.id === id ? updated : s)),
      }));
      return updated;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update tool server';
      set({ error: message });
      throw err;
    }
  },

  deleteToolServer: async (id: string) => {
    set({ error: null });
    try {
      await api.deleteToolServer(id);
      set((state) => ({
        toolServers: state.toolServers.filter((s) => s.id !== id),
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete tool server';
      set({ error: message });
      throw err;
    }
  },
}));
