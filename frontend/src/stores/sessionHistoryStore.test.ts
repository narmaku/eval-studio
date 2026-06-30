import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useSessionHistoryStore } from './sessionHistoryStore';
import type { Session } from '@/types';

vi.mock('@/services/api', () => ({
  api: {
    listSessions: vi.fn(),
    updateSession: vi.fn(),
    deleteSession: vi.fn(),
  },
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 'sess-1',
  evaluation_id: null,
  name: 'Test Session',
  mode: 'agent',
  status: 'ended',
  transcript: null,
  agent_config: null,
  judge_config_snapshot: null,
  scores: null,
  error: null,
  tags: [],
  started_at: '2026-01-01T00:00:00Z',
  ended_at: '2026-01-01T01:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('sessionHistoryStore', () => {
  beforeEach(() => {
    useSessionHistoryStore.setState({
      sessions: [],
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useSessionHistoryStore.getState();
    expect(state.sessions).toEqual([]);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  describe('fetchSessions', () => {
    it('populates sessions from API response', async () => {
      const sessions = [makeSession({ id: 'sess-1' }), makeSession({ id: 'sess-2' })];
      mockedApi.listSessions.mockResolvedValue({
        items: sessions,
        total: 2,
        page: 1,
        page_size: 50,
        pages: 1,
      });

      await useSessionHistoryStore.getState().fetchSessions();

      const state = useSessionHistoryStore.getState();
      expect(state.sessions).toEqual(sessions);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('sets error on API failure', async () => {
      mockedApi.listSessions.mockRejectedValue(new Error('Network error'));

      await expect(useSessionHistoryStore.getState().fetchSessions()).rejects.toThrow(
        'Network error',
      );

      const state = useSessionHistoryStore.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });
  });

  describe('updateSession', () => {
    it('updates session in list on success', async () => {
      const original = makeSession();
      useSessionHistoryStore.setState({ sessions: [original] });

      const updated = { ...original, name: 'Renamed Session', tags: ['tagged'] };
      mockedApi.updateSession.mockResolvedValue(updated);

      const result = await useSessionHistoryStore
        .getState()
        .updateSession('sess-1', { name: 'Renamed Session', tags: ['tagged'] });

      expect(result).toEqual(updated);
      expect(useSessionHistoryStore.getState().sessions[0]?.name).toBe('Renamed Session');
      expect(useSessionHistoryStore.getState().error).toBeNull();
    });

    it('sets error and re-throws on failure', async () => {
      useSessionHistoryStore.setState({ sessions: [makeSession()] });
      mockedApi.updateSession.mockRejectedValue(new Error('Forbidden'));

      await expect(
        useSessionHistoryStore.getState().updateSession('sess-1', { name: 'fail' }),
      ).rejects.toThrow('Forbidden');

      expect(useSessionHistoryStore.getState().error).toBe('Forbidden');
    });
  });

  describe('deleteSession', () => {
    it('removes session from list on success', async () => {
      const s1 = makeSession({ id: 'sess-1' });
      const s2 = makeSession({ id: 'sess-2', name: 'Keep' });
      useSessionHistoryStore.setState({ sessions: [s1, s2] });
      mockedApi.deleteSession.mockResolvedValue(undefined);

      await useSessionHistoryStore.getState().deleteSession('sess-1');

      expect(useSessionHistoryStore.getState().sessions).toHaveLength(1);
      expect(useSessionHistoryStore.getState().sessions[0]?.id).toBe('sess-2');
    });

    it('sets error and re-throws on failure', async () => {
      useSessionHistoryStore.setState({ sessions: [makeSession()] });
      mockedApi.deleteSession.mockRejectedValue(new Error('Not found'));

      await expect(useSessionHistoryStore.getState().deleteSession('sess-1')).rejects.toThrow(
        'Not found',
      );

      expect(useSessionHistoryStore.getState().error).toBe('Not found');
    });
  });
});
