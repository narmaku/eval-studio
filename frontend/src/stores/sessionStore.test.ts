import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSessionStore } from './sessionStore';

vi.mock('@/services/api', () => ({
  api: {
    createSession: vi.fn(),
    endSession: vi.fn(),
    scoreSession: vi.fn(),
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
    expect(state.isScoring).toBe(false);
    expect(state.error).toBeNull();
  });

  describe('createSession', () => {
    it('creates session and sets currentSession on success', async () => {
      const mockSession = {
        id: 'sess-1',
        evaluation_id: 'eval-1',
        mode: 'live' as const,
        status: 'active' as const,

        agent_config: null,
        judge_config_snapshot: null,
        transcript: [],
        name: null,
        scores: null,
        error: null,
        started_at: '2026-01-01T00:00:00Z',
        ended_at: null,
        created_at: '2026-01-01T00:00:00Z',
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

  describe('scoreSession', () => {
    it('calls api.scoreSession and updates session and scores on success', async () => {
      const scoredSession = {
        id: 'sess-1',
        evaluation_id: 'eval-1',
        mode: 'live' as const,
        status: 'completed' as const,
        agent_config: null,
        judge_config_snapshot: { provider_id: 'judge-provider-1' },
        transcript: [],
        name: null,
        scores: {
          overall: 0.85,
          passed: true,
          reasoning: 'Good answers',
          breakdown: { accuracy: 0.9, relevance: 0.8 },
        },
        error: null,
        started_at: '2026-01-01T00:00:00Z',
        ended_at: '2026-01-01T00:10:00Z',
        created_at: '2026-01-01T00:00:00Z',
      };

      mockedApi.scoreSession.mockResolvedValue(scoredSession);

      useSessionStore.setState({
        currentSession: {
          id: 'sess-1',
          evaluation_id: 'eval-1',
          mode: 'live',
          status: 'ended',
          agent_config: null,
          judge_config_snapshot: { provider_id: 'judge-provider-1' },
          transcript: [],
          name: null,
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: '2026-01-01T00:10:00Z',
          created_at: '2026-01-01T00:00:00Z',
        },
      });

      await useSessionStore.getState().scoreSession({ provider_id: 'judge-provider-1' });

      const state = useSessionStore.getState();
      expect(state.currentSession?.status).toBe('completed');
      expect(state.scores).toHaveLength(1);
      expect(state.scores[0]!.overall).toBe(0.85);
      expect(state.scores[0]!.dimensions).toEqual({ accuracy: 0.9, relevance: 0.8 });
      expect(state.isScoring).toBe(false);
      expect(state.error).toBeNull();
      expect(mockedApi.scoreSession).toHaveBeenCalledWith('sess-1', {
        provider_id: 'judge-provider-1',
      });
    });

    it('sets error and keeps isScoring false on failure', async () => {
      mockedApi.scoreSession.mockRejectedValue(new Error('Judge unavailable'));

      useSessionStore.setState({
        currentSession: {
          id: 'sess-1',
          evaluation_id: 'eval-1',
          mode: 'live',
          status: 'ended',
          agent_config: null,
          judge_config_snapshot: null,
          transcript: [],
          name: null,
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: '2026-01-01T00:10:00Z',
          created_at: '2026-01-01T00:00:00Z',
        },
      });

      await expect(
        useSessionStore.getState().scoreSession({ provider_id: 'judge-provider-1' }),
      ).rejects.toThrow('Judge unavailable');

      const state = useSessionStore.getState();
      expect(state.isScoring).toBe(false);
      expect(state.error).toBe('Judge unavailable');
    });

    it('does nothing when no current session', async () => {
      await useSessionStore.getState().scoreSession({ provider_id: 'judge-provider-1' });
      expect(mockedApi.scoreSession).not.toHaveBeenCalled();
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

          agent_config: null,
          judge_config_snapshot: null,
          transcript: [],
          name: null,
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: null,
          created_at: '2026-01-01T00:00:00Z',
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

  describe('endSession', () => {
    it('uses REST only — no WS end_session frame is sent (FE-003)', async () => {
      const endedSession = {
        id: 'sess-1',
        evaluation_id: 'eval-1',
        mode: 'live' as const,
        status: 'ended' as const,
        agent_config: null,
        judge_config_snapshot: null,
        transcript: [],
        name: null,
        scores: null,
        error: null,
        started_at: '2026-01-01T00:00:00Z',
        ended_at: '2026-01-01T00:10:00Z',
        created_at: '2026-01-01T00:00:00Z',
      };

      mockedApi.endSession.mockResolvedValue(endedSession);

      useSessionStore.setState({
        currentSession: {
          id: 'sess-1',
          evaluation_id: 'eval-1',
          mode: 'live',
          status: 'active',
          agent_config: null,
          judge_config_snapshot: null,
          transcript: [],
          name: null,
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      });

      // Connect WS
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      // End the session
      await useSessionStore.getState().endSession();

      // REST should have been called
      expect(mockedApi.endSession).toHaveBeenCalledWith('sess-1');

      // WS should NOT have been sent an end_session frame
      const wsSent = ws.sent.map((s) => JSON.parse(s));
      const endFrames = wsSent.filter((m: Record<string, unknown>) => m.type === 'end_session');
      expect(endFrames).toHaveLength(0);

      // Session should be updated
      expect(useSessionStore.getState().currentSession?.status).toBe('ended');

      // WS should be disconnected
      expect(useSessionStore.getState().isConnected).toBe(false);
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

          agent_config: null,
          judge_config_snapshot: null,
          transcript: [],
          name: null,
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: null,
          created_at: '2026-01-01T00:00:00Z',
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
      expect(state.isScoring).toBe(false);
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
      expect(useSessionStore.getState().toolCalls[0]).toEqual({ ...toolCall, status: 'pending' });
    });

    it('handles connected by setting isConnected', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      ws.simulateMessage({
        type: 'connected',
        data: { session_id: 'sess-1' },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().isConnected).toBe(true);
    });

    it('handles session_ended by updating session status', () => {
      useSessionStore.setState({
        currentSession: {
          id: 'sess-1',
          evaluation_id: 'eval-1',
          mode: 'live',
          status: 'active',

          agent_config: null,
          judge_config_snapshot: null,
          transcript: [],
          name: null,
          scores: null,
          error: null,
          started_at: '2026-01-01T00:00:00Z',
          ended_at: null,
          created_at: '2026-01-01T00:00:00Z',
        },
        isProcessing: true,
      });
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      ws.simulateMessage({
        type: 'session_ended',
        data: { status: 'ended', ended_at: '2026-01-01T00:10:00Z' },
        timestamp: '2026-01-01T00:10:00Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().currentSession?.status).toBe('ended');
      expect(useSessionStore.getState().currentSession?.ended_at).toBe('2026-01-01T00:10:00Z');
      expect(useSessionStore.getState().isProcessing).toBe(false);
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

    it('handles tool_executing by setting tool call status to executing', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      // First add a tool_call with pending status
      ws.simulateMessage({
        type: 'tool_call',
        data: {
          id: 'tc-exec-1',
          tool_name: 'read_file',
          arguments: { path: '/etc/hosts' },
          result: null,
          duration_ms: 0,
          timestamp: '2026-01-01T00:00:01Z',
          status: 'pending',
        },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().toolCalls).toHaveLength(1);
      expect(useSessionStore.getState().toolCalls[0]!.status).toBe('pending');

      // Now simulate tool_executing
      ws.simulateMessage({
        type: 'tool_executing',
        data: { tool_call_id: 'tc-exec-1', tool_name: 'read_file' },
        timestamp: '2026-01-01T00:00:02Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().toolCalls[0]!.status).toBe('executing');
    });

    it('handles tool_result by setting tool call status and result', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      // Add a pending tool_call
      ws.simulateMessage({
        type: 'tool_call',
        data: {
          id: 'tc-result-1',
          tool_name: 'search',
          arguments: { query: 'test' },
          result: null,
          duration_ms: 0,
          timestamp: '2026-01-01T00:00:01Z',
          status: 'pending',
        },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      // Simulate tool_result
      ws.simulateMessage({
        type: 'tool_result',
        data: {
          tool_call_id: 'tc-result-1',
          tool_name: 'search',
          result: 'Found 3 results',
          is_error: false,
          duration_ms: 150,
        },
        timestamp: '2026-01-01T00:00:02Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      const tc = useSessionStore.getState().toolCalls[0]!;
      expect(tc.status).toBe('completed');
      expect(tc.result).toBe('Found 3 results');
      expect(tc.duration_ms).toBe(150);
    });

    it('handles tool_result with error by setting status to error', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      // Add a pending tool_call
      ws.simulateMessage({
        type: 'tool_call',
        data: {
          id: 'tc-err-1',
          tool_name: 'bad_tool',
          arguments: {},
          result: null,
          duration_ms: 0,
          timestamp: '2026-01-01T00:00:01Z',
          status: 'pending',
        },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      // Simulate error tool_result
      ws.simulateMessage({
        type: 'tool_result',
        data: {
          tool_call_id: 'tc-err-1',
          tool_name: 'bad_tool',
          result: 'Tool crashed',
          is_error: true,
          duration_ms: 5,
        },
        timestamp: '2026-01-01T00:00:02Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      const tc = useSessionStore.getState().toolCalls[0]!;
      expect(tc.status).toBe('error');
      expect(tc.result).toBe('Tool crashed');
    });

    it('keeps isProcessing true during tool execution, sets false on message_complete', () => {
      useSessionStore.setState({ isProcessing: true });
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      // Add a tool_call
      ws.simulateMessage({
        type: 'tool_call',
        data: {
          id: 'tc-proc-1',
          tool_name: 'search',
          arguments: {},
          result: null,
          duration_ms: 0,
          timestamp: '2026-01-01T00:00:01Z',
          status: 'pending',
        },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      // isProcessing should remain true
      expect(useSessionStore.getState().isProcessing).toBe(true);

      // tool_executing
      ws.simulateMessage({
        type: 'tool_executing',
        data: { tool_call_id: 'tc-proc-1', tool_name: 'search' },
        timestamp: '2026-01-01T00:00:02Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().isProcessing).toBe(true);

      // tool_result
      ws.simulateMessage({
        type: 'tool_result',
        data: {
          tool_call_id: 'tc-proc-1',
          tool_name: 'search',
          result: 'done',
          is_error: false,
          duration_ms: 50,
        },
        timestamp: '2026-01-01T00:00:03Z',
        sender: 'system',
        session_id: 'sess-1',
      });

      // Still processing (waiting for LLM response)
      expect(useSessionStore.getState().isProcessing).toBe(true);

      // message_complete ends processing
      ws.simulateMessage({
        type: 'message_complete',
        data: { content: 'Here are the results.', message_id: 'msg-1', tool_calls: [] },
        timestamp: '2026-01-01T00:00:04Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().isProcessing).toBe(false);
    });

    it('does not duplicate tool calls already received via tool_call envelope', () => {
      useSessionStore.getState().connectWebSocket('sess-1');
      const ws = getWs();
      ws.simulateOpen();

      // Receive tool_call envelope during agentic loop
      ws.simulateMessage({
        type: 'tool_call',
        data: {
          id: 'tc-dedup-1',
          tool_name: 'search',
          arguments: { query: 'test' },
          result: null,
          duration_ms: 0,
          timestamp: '2026-01-01T00:00:01Z',
          status: 'pending',
        },
        timestamp: '2026-01-01T00:00:01Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      expect(useSessionStore.getState().toolCalls).toHaveLength(1);

      // message_complete includes the same tool call
      ws.simulateMessage({
        type: 'message_complete',
        data: {
          content: 'Done',
          message_id: 'msg-1',
          tool_calls: [
            {
              id: 'tc-dedup-1',
              tool_name: 'search',
              arguments: { query: 'test' },
              result: 'found',
              duration_ms: 100,
              timestamp: '2026-01-01T00:00:01Z',
              status: 'completed',
            },
          ],
        },
        timestamp: '2026-01-01T00:00:02Z',
        sender: 'agent',
        session_id: 'sess-1',
      });

      // Should still have only 1 tool call (no duplicate)
      expect(useSessionStore.getState().toolCalls).toHaveLength(1);
    });
  });
});
