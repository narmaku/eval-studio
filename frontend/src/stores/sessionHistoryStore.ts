import { create } from 'zustand';
import type { Session, UpdateSessionRequest } from '@/types';
import { api } from '@/services/api';

interface SessionHistoryStore {
  sessions: Session[];
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchSessions: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    evaluation_id?: string;
  }) => Promise<void>;
  updateSession: (id: string, data: UpdateSessionRequest) => Promise<Session>;
  deleteSession: (id: string) => Promise<void>;
}

export const useSessionHistoryStore = create<SessionHistoryStore>((set, get) => ({
  sessions: [],
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchSessions: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.listSessions({ page_size: 50, ...params });
      set({ sessions: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch sessions';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  updateSession: async (id: string, data: UpdateSessionRequest) => {
    set({ error: null });
    try {
      const updated = await api.updateSession(id, data);
      set((state) => ({
        sessions: state.sessions.map((s) => (s.id === id ? updated : s)),
      }));
      return updated;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update session';
      set({ error: message });
      throw err;
    }
  },

  deleteSession: async (id: string) => {
    set({ error: null });
    try {
      await api.deleteSession(id);
      set({
        sessions: get().sessions.filter((s) => s.id !== id),
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete session';
      set({ error: message });
      throw err;
    }
  },
}));
