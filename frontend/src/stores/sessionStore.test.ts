import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSessionStore } from './sessionStore';

vi.mock('@/services/api', () => ({
  api: {
    createSession: vi.fn(),
    endSession: vi.fn(),
  },
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  readonly CONNECTING = 0;
  readonly OPEN = 1;
  readonly CLOSING = 2;
  readonly CLOSED = 3;

  url: string;
  readyState: number = 0; // CONNECTING
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Test helpers
  simulateOpen() {
    this.readyState = 1; // OPEN
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  simulateMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  simulateClose() {
    this.readyState = 3; // CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

/** Helper to get the latest MockWebSocket instance, asserting it exists. */
function getWs(): MockWebSocket {
  const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1];
  if (!ws) throw new Error('No MockWebSocket instance found');
  return ws;
}

describe('sessionStore', () => {
  beforeEach(() => {
    useSessionStore.setState({
      currentSession: null,
      messages: [],
      toolCalls: [],
      scores: [],
      isConnected: false,
      isProcessing: false,
      error: null,
    });
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('has correct initial state', () => {
    const state = useSessionStore.getState();
    expect(state.currentSession).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.toolCalls).toEqual([]);
    expect(state.scores).toEqual([]);
    expect(state.isConnected).toBe(false);
    expect(state.isProcessing).toBe(false);
    expect(state.error).toBeNull();
  });

  describe('createSession', () => {
    it('creates session and sets currentSession on success', async () => {
      const mockSession = {
        id: 'sess-1',
        evaluation_id: 'eval-1',
        mode: 'live' as const,
        status: 'active' as const,
        environment_id: null,
        scenario_id: null,
        agent_config: null,
        judge_config_snapshot: null,
        messages: [],
        tool_calls: [],
        scores: null,
        error: null,
        started_at: '2026-01-01T00:00:00Z',
        ended_at: null,
        turn_count: 0,
      };

      mockedApi.createSession.mockResolvedValue(mockSession);

      await useSessionStore.getState().createSession({
        evaluation_id: 'eval-1',
        mode: 'live',
      });

      const state = useSessionStore.getState();
      expect(state.currentSession).toEqual(mockSession);
      expect(mockedApi.createSession).toHaveBeenCalledWith({
        evaluation_id: 'eval-1',
        mode: 'live',
      });
    });

    it('sets error on API failure', async () => {
      mockedApi.createSession.mockRejectedValue(new Error('Network error'));

      await useSessionStore.getState().createSession({
        evaluation_id: 'eval-1',
        mode: 'live',
      });

      const state = useSessionStore.getState();
      expect(state.currentSession).toBeNull();
      expect(state.error).toBe('Network error');
    });
  });

  describe('sendMessage', () => {
    it('adds user message to messages and sets isProcessing', () => {
      useSessionStore.setState({
        currentSession: {
          id: 'sess-1',
          evaluation_id: 'eval-1',
          mode: 'live',
          status: 'active',
          environment_id: null,
          scenario_id: null,
          agent_config: null,
          judge_config_snapshot: null,
          messages: [],
          tool_calls: [],
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: null,
          turn_count: 0,
        },
        isConnected: true,
      });

      // Connect WS so sendMessage can use it
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      useSessionStore.getState().sendMessage('Hello agent');

      const state = useSessionStore.getState();
      expect(state.messages).toHaveLength(1);
      const firstMsg = state.messages[0];
      expect(firstMsg).toBeDefined();
      expect(firstMsg!.sender).toBe('user');
      expect(firstMsg!.content).toBe('Hello agent');
      expect(state.isProcessing).toBe(true);
    });

    it('does nothing when no session is active', () => {
      useSessionStore.getState().sendMessage('Hello');

      const state = useSessionStore.getState();
      expect(state.messages).toEqual([]);
      expect(state.isProcessing).toBe(false);
    });
  });

  describe('resetSession', () => {
    it('clears all state for new session', () => {
      useSessionStore.setState({
        currentSession: {
          id: 'sess-1',
          evaluation_id: 'eval-1',
          mode: 'live',
          status: 'active',
          environment_id: null,
          scenario_id: null,
          agent_config: null,
          judge_config_snapshot: null,
          messages: [],
          tool_calls: [],
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: null,
          turn_count: 0,
        },
        messages: [
          {
            id: 'msg-1',
            sender: 'user',
            content: 'Hello',
            timestamp: '2026-01-01T00:00:00Z',
          },
        ],
        toolCalls: [
          {
            id: 'tc-1',
            tool_name: 'search',
            arguments: {},
            result: null,
            duration_ms: 100,
            timestamp: '2026-01-01T00:00:00Z',
          },
        ],
        scores: [
          {
            turn_number: null,
            dimensions: { accuracy: 0.8 },
            overall: 0.8,
            judge_reasoning: 'Good',
          },
        ],
        isConnected: true,
        isProcessing: true,
        error: 'some error',
      });

      useSessionStore.getState().resetSession();

      const state = useSessionStore.getState();
      expect(state.currentSession).toBeNull();
      expect(state.messages).toEqual([]);
      expect(state.toolCalls).toEqual([]);
      expect(state.scores).toEqual([]);
      expect(state.isConnected).toBe(false);
      expect(state.isProcessing).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('WebSocket connection', () => {
    it('connects and sets isConnected on open', () => {
      useSessionStore.getState().connectWebSocket('sess-1');

      expect(MockWebSocket.instances).toHaveLength(1);
      const ws = getWs();
      expect(ws.url).toContain('sess-1');

      // Simulate connection open
      ws.simulateOpen();

      expect(useSessionStore.getState().isConnected).toBe(true);
    });

    it('sets isConnected false on close', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();
      expect(useSessionStore.getState().isConnected).toBe(true);

      ws.simulateClose();
      expect(useSessionStore.getState().isConnected).toBe(false);
    });

    it('handles message_chunk by appending content to last agent message', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      // Simulate a message chunk
      ws.simulateMessage({
        type: 'message_chunk',
        data: { content: 'Hello ', message_id: 'msg-agent-1' },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      let state = useSessionStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0]!.content).toBe('Hello ');
      expect(state.messages[0]!.sender).toBe('agent');

      // Send another chunk
      ws.simulateMessage({
        type: 'message_chunk',
        data: { content: 'world!', message_id: 'msg-agent-1' },
        timestamp: '2026-01-01T00:00:02Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      state = useSessionStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0]!.content).toBe('Hello world!');
    });

    it('handles message_complete by finalizing agent message', () => {
      useSessionStore.setState({ isProcessing: true });
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      ws.simulateMessage({
        type: 'message_complete',
        data: { content: 'Final answer', message_id: 'msg-agent-1', tool_calls: [] },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      const state = useSessionStore.getState();
      expect(state.isProcessing).toBe(false);
      // Should have a finalized message
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0]!.content).toBe('Final answer');
    });

    it('handles tool_call by appending to toolCalls', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      const toolCall = {
        id: 'tc-1',
        tool_name: 'search',
        arguments: { query: 'test' },
        result: { results: [] },
        duration_ms: 150,
        timestamp: '2026-01-01T00:00:01Z',
      };

      ws.simulateMessage({
        type: 'tool_call',
        data: toolCall,
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().toolCalls).toHaveLength(1);
      expect(useSessionStore.getState().toolCalls[0]).toEqual(toolCall);
    });

    it('handles score by appending to scores', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      const score = {
        turn_number: null,
        dimensions: { accuracy: 0.9 },
        overall: 0.9,
        judge_reasoning: 'Excellent response',
      };

      ws.simulateMessage({
        type: 'score',
        data: score,
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'judge',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().scores).toHaveLength(1);
      expect(useSessionStore.getState().scores[0]).toEqual(score);
    });

    it('handles status update', () => {
      useSessionStore.setState({
        currentSession: {
          id: 'sess-1',
          evaluation_id: 'eval-1',
          mode: 'live',
          status: 'active',
          environment_id: null,
          scenario_id: null,
          agent_config: null,
          judge_config_snapshot: null,
          messages: [],
          tool_calls: [],
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: null,
          turn_count: 0,
        },
      });
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      ws.simulateMessage({
        type: 'status',
        data: { status: 'completed' },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().currentSession?.status).toBe('completed');
    });

    it('handles error message', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      ws.simulateMessage({
        type: 'error',
        data: { message: 'Something went wrong', code: 'INTERNAL_ERROR' },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().error).toBe('Something went wrong');
    });

    it('disconnectWebSocket closes connection', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();
      expect(useSessionStore.getState().isConnected).toBe(true);

      useSessionStore.getState().disconnectWebSocket();
      expect(useSessionStore.getState().isConnected).toBe(false);
    });
  });
});
