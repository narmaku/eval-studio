import { create } from 'zustand';
import type { Session } from '@/types';
import { api } from '@/services/api';

interface SessionHistoryStore {
  sessions: Session[];
  isLoading: boolean;
  error: string | null;

  fetchSessions: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    evaluation_id?: string;
  }) => Promise<void>;
}

export const useSessionHistoryStore = create<SessionHistoryStore>((set) => ({
  sessions: [],
  isLoading: false,
  error: null,

  fetchSessions: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.listSessions({ page_size: 50, ...params });
      set({ sessions: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch sessions';
      set({ error: message, isLoading: false });
    }
  },
}));
