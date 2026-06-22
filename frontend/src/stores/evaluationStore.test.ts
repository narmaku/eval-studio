import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useEvaluationStore } from './evaluationStore';

vi.mock('@/services/api', () => ({
  api: {
    listEvaluations: vi.fn(),
    getEvaluation: vi.fn(),
    createEvaluation: vi.fn(),
    runEvaluation: vi.fn(),
    rerunEvaluation: vi.fn(),
  },
  getWsAuthParam: vi.fn(() => ''),
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onopen: (() => void) | null = null;
  readyState = 1; // OPEN
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    // Simulate async open
    setTimeout(() => this.onopen?.(), 0);
  }

  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateClose() {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  }
}

vi.stubGlobal('WebSocket', MockWebSocket);

describe('evaluationStore', () => {
  beforeEach(() => {
    useEvaluationStore.setState({
      evaluations: [],
      currentEvaluation: null,
      isLoading: false,
      error: null,
      logs: [],
      progress: null,
      wsConnection: null,
      _connectedEvaluationId: null,
    });
    vi.clearAllMocks();
    sessionStorageMock.clear();
    MockWebSocket.instances = [];
  });

  afterEach(() => {
    // Clean up WebSocket connections
    const state = useEvaluationStore.getState();
    if (state.wsConnection) {
      state.disconnectFromEvaluation();
    }
  });

  it('has correct initial state', () => {
    const state = useEvaluationStore.getState();
    expect(state.evaluations).toEqual([]);
    expect(state.currentEvaluation).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
    expect(state.logs).toEqual([]);
    expect(state.progress).toBeNull();
    expect(state._connectedEvaluationId).toBeNull();
  });

  it('can set and clear error', () => {
    const { setError, clearError } = useEvaluationStore.getState();
    setError('Something went wrong');
    expect(useEvaluationStore.getState().error).toBe('Something went wrong');
    clearError();
    expect(useEvaluationStore.getState().error).toBeNull();
  });

  it('can set loading state', () => {
    const { setLoading } = useEvaluationStore.getState();
    setLoading(true);
    expect(useEvaluationStore.getState().isLoading).toBe(true);
    setLoading(false);
    expect(useEvaluationStore.getState().isLoading).toBe(false);
  });

  describe('fetchEvaluations', () => {
    it('sets loading, stores evaluations, clears loading on success', async () => {
      const mockEvaluations = [
        {
          id: 'e1',
          name: 'Test Eval',
          mode: 'qa' as const,
          status: 'completed' as const,
          dataset_id: 'd1',
          judge_config_id: 'j1',
          config: {
            model_endpoint: { name: 'test', default_model: 'gpt-4' },
            judge_config: { preset: 'default' },
          },
          result_count: 5,
          average_score: null,
          pass_rate: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T01:00:00Z',
        },
      ];
      mockedApi.listEvaluations.mockResolvedValue({
        items: mockEvaluations,
        total: 1,
        page: 1,
        page_size: 20,
        pages: 1,
      });

      const promise = useEvaluationStore.getState().fetchEvaluations();
      expect(useEvaluationStore.getState().isLoading).toBe(true);
      expect(useEvaluationStore.getState().error).toBeNull();

      await promise;

      expect(useEvaluationStore.getState().isLoading).toBe(false);
      expect(useEvaluationStore.getState().evaluations).toEqual(mockEvaluations);
      expect(mockedApi.listEvaluations).toHaveBeenCalledWith({});
    });

    it('passes mode and status filters when provided', async () => {
      mockedApi.listEvaluations.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        pages: 0,
      });

      await useEvaluationStore.getState().fetchEvaluations({ mode: 'qa', status: 'completed' });

      expect(mockedApi.listEvaluations).toHaveBeenCalledWith({ mode: 'qa', status: 'completed' });
    });

    it('handles API error: sets error string', async () => {
      mockedApi.listEvaluations.mockRejectedValue(new Error('Network error'));

      await useEvaluationStore.getState().fetchEvaluations();

      expect(useEvaluationStore.getState().isLoading).toBe(false);
      expect(useEvaluationStore.getState().error).toBe('Network error');
      expect(useEvaluationStore.getState().evaluations).toEqual([]);
    });
  });

  describe('connectToEvaluation', () => {
    it('creates WebSocket connection with correct URL', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(MockWebSocket.instances[0]!.url).toContain('/ws/progress/eval-123');
    });

    it('updates progress on progress message', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');
      const ws = MockWebSocket.instances[0]!;

      ws.simulateMessage({
        type: 'progress',
        evaluation_id: 'eval-123',
        completed: 5,
        total: 10,
        current_item: 'What is RHEL?',
      });

      const state = useEvaluationStore.getState();
      expect(state.progress).toEqual({
        completed: 5,
        total: 10,
        currentItem: 'What is RHEL?',
      });
    });

    it('appends log entries on log message', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');
      const ws = MockWebSocket.instances[0]!;

      ws.simulateMessage({
        type: 'log',
        evaluation_id: 'eval-123',
        timestamp: '2026-06-02T10:00:00Z',
        level: 'info',
        message: 'Processing item 1/10',
      });

      const state = useEvaluationStore.getState();
      expect(state.logs).toHaveLength(1);
      expect(state.logs[0]!.message).toBe('Processing item 1/10');
      expect(state.logs[0]!.level).toBe('info');
    });

    it('updates currentEvaluation status on status message', () => {
      useEvaluationStore.setState({
        currentEvaluation: {
          id: 'eval-123',
          name: 'Test Eval',
          mode: 'qa',
          status: 'running',
          dataset_id: 'd1',
          judge_config_id: null,
          config: {
            model_endpoint: { name: 'test', default_model: 'gpt-4' },
            judge_config: { preset: 'default' },
          },
          result_count: null,
          average_score: null,
          pass_rate: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T01:00:00Z',
        },
      });

      useEvaluationStore.getState().connectToEvaluation('eval-123');
      const ws = MockWebSocket.instances[0]!;

      ws.simulateMessage({
        type: 'status',
        evaluation_id: 'eval-123',
        status: 'completed',
      });

      const state = useEvaluationStore.getState();
      expect(state.currentEvaluation?.status).toBe('completed');
    });

    it('clears running evaluation on terminal status message', () => {
      useEvaluationStore.setState({
        currentEvaluation: {
          id: 'eval-123',
          name: 'Test Eval',
          mode: 'qa',
          status: 'running',
          dataset_id: 'd1',
          judge_config_id: null,
          config: {
            model_endpoint: { name: 'test', default_model: 'gpt-4' },
            judge_config: { preset: 'default' },
          },
          result_count: null,
          average_score: null,
          pass_rate: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T01:00:00Z',
        },
      });

      // Persist a running evaluation first
      useEvaluationStore.getState().persistRunningEvaluation({
        id: 'eval-123',
        name: 'Test Eval',
        mode: 'qa',
      });

      useEvaluationStore.getState().connectToEvaluation('eval-123');
      const ws = MockWebSocket.instances[0]!;

      ws.simulateMessage({
        type: 'status',
        evaluation_id: 'eval-123',
        status: 'failed',
      });

      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('runningEvaluation');
    });

    it('updates progress with contestant_model for arena', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-arena');
      const ws = MockWebSocket.instances[0]!;

      ws.simulateMessage({
        type: 'progress',
        evaluation_id: 'eval-arena',
        completed: 3,
        total: 8,
        current_item: 'What is Fedora?',
        contestant_model: 'model-a',
      });

      const state = useEvaluationStore.getState();
      expect(state.progress?.contestantModel).toBe('model-a');
    });

    it('skips reconnect if already connected to the same evaluation', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');
      expect(MockWebSocket.instances).toHaveLength(1);

      // Simulate logs arriving on the first connection
      const ws = MockWebSocket.instances[0]!;
      ws.simulateMessage({
        type: 'log',
        evaluation_id: 'eval-123',
        timestamp: '2026-06-02T10:00:00Z',
        level: 'info',
        message: 'First log',
      });
      expect(useEvaluationStore.getState().logs).toHaveLength(1);

      // Second call for the same evaluation should be a no-op
      useEvaluationStore.getState().connectToEvaluation('eval-123');

      // No new WebSocket was created
      expect(MockWebSocket.instances).toHaveLength(1);
      // Logs were NOT wiped
      expect(useEvaluationStore.getState().logs).toHaveLength(1);
      expect(useEvaluationStore.getState().logs[0]!.message).toBe('First log');
    });

    it('reconnects when connecting to a different evaluation', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');
      expect(MockWebSocket.instances).toHaveLength(1);
      const firstWs = MockWebSocket.instances[0]!;

      useEvaluationStore.getState().connectToEvaluation('eval-456');
      expect(MockWebSocket.instances).toHaveLength(2);
      expect(firstWs.close).toHaveBeenCalled();
      expect(useEvaluationStore.getState()._connectedEvaluationId).toBe('eval-456');
    });

    it('tracks _connectedEvaluationId', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');
      expect(useEvaluationStore.getState()._connectedEvaluationId).toBe('eval-123');
    });
  });

  describe('createAndRunEvaluation', () => {
    it('connects WebSocket before triggering the background task', async () => {
      vi.useFakeTimers();

      const pendingEval = {
        id: 'eval-new',
        name: 'New Eval',
        mode: 'qa' as const,
        status: 'pending' as const,
        dataset_id: 'd1',

        judge_config_id: null,
        config: {
          model_endpoint: { name: 'test', default_model: 'gpt-4' },
          judge_config: { preset: 'default' },
        },
        result_count: null,
        average_score: null,
        pass_rate: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      };
      const runningEval = { ...pendingEval, status: 'running' as const };

      // Track call order
      const callOrder: string[] = [];
      mockedApi.createEvaluation.mockImplementation(async () => {
        callOrder.push('createEvaluation');
        return pendingEval;
      });
      mockedApi.runEvaluation.mockImplementation(async () => {
        callOrder.push('runEvaluation');
        return runningEval;
      });

      const promise = useEvaluationStore.getState().createAndRunEvaluation({
        name: 'New Eval',
        mode: 'qa',
        dataset_id: 'd1',
        config: {
          model_endpoint: { name: 'test', default_model: 'gpt-4' },
          judge_config: { preset: 'default' },
        },
      });

      const result = await promise;

      expect(callOrder).toEqual(['createEvaluation', 'runEvaluation']);
      expect(result.status).toBe('running');
      // WS connected after run (replay buffer ensures no messages lost)
      expect(MockWebSocket.instances).toHaveLength(1);
      expect(useEvaluationStore.getState()._connectedEvaluationId).toBe('eval-new');

      vi.useRealTimers();
    });
  });

  describe('disconnectFromEvaluation', () => {
    it('closes the WebSocket connection and clears tracked evaluation ID', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');
      const ws = MockWebSocket.instances[0]!;

      useEvaluationStore.getState().disconnectFromEvaluation();

      expect(ws.close).toHaveBeenCalled();
      expect(useEvaluationStore.getState().wsConnection).toBeNull();
      expect(useEvaluationStore.getState()._connectedEvaluationId).toBeNull();
    });
  });

  describe('log buffer cap', () => {
    it('caps logs at 500 entries', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-cap');
      const ws = MockWebSocket.instances[0]!;

      for (let i = 1; i <= 600; i++) {
        ws.simulateMessage({
          type: 'log',
          evaluation_id: 'eval-cap',
          timestamp: `2026-06-02T10:00:${String(i).padStart(2, '0')}Z`,
          level: 'info',
          message: `Log ${i}`,
        });
      }

      const logs = useEvaluationStore.getState().logs;
      expect(logs).toHaveLength(500);
      expect(logs[0]!.message).toBe('Log 101');
      expect(logs[499]!.message).toBe('Log 600');
    });
  });

  describe('clearLogs', () => {
    it('resets logs array', () => {
      useEvaluationStore.getState().connectToEvaluation('eval-123');
      const ws = MockWebSocket.instances[0]!;

      ws.simulateMessage({
        type: 'log',
        evaluation_id: 'eval-123',
        timestamp: '2026-06-02T10:00:00Z',
        level: 'info',
        message: 'test log',
      });

      expect(useEvaluationStore.getState().logs).toHaveLength(1);

      useEvaluationStore.getState().clearLogs();
      expect(useEvaluationStore.getState().logs).toEqual([]);
    });
  });

  describe('sessionStorage persistence', () => {
    it('persists running evaluation to sessionStorage', () => {
      useEvaluationStore.getState().persistRunningEvaluation({
        id: 'eval-123',
        name: 'Test Eval',
        mode: 'qa',
      });

      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        'runningEvaluation',
        JSON.stringify({ id: 'eval-123', name: 'Test Eval', mode: 'qa' }),
      );
    });

    it('clears running evaluation from sessionStorage', () => {
      useEvaluationStore.getState().clearRunningEvaluation();

      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('runningEvaluation');
    });

    it('getRunningEvaluation returns persisted evaluation', () => {
      sessionStorageMock.getItem.mockReturnValueOnce(
        JSON.stringify({ id: 'eval-123', name: 'Test Eval', mode: 'qa' }),
      );

      const result = useEvaluationStore.getState().getRunningEvaluation();
      expect(result).toEqual({ id: 'eval-123', name: 'Test Eval', mode: 'qa' });
    });

    it('getRunningEvaluation returns null when nothing persisted', () => {
      sessionStorageMock.getItem.mockReturnValueOnce(null);

      const result = useEvaluationStore.getState().getRunningEvaluation();
      expect(result).toBeNull();
    });
  });
});
