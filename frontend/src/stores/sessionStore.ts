import { create } from 'zustand';
import type {
  Session,
  Message,
  ToolCall,
  SessionScore,
  CreateSessionRequest,
  WsEnvelope,
  WsMessageChunk,
  WsMessageComplete,
  WsToolCallMessage,
  WsToolExecutingMessage,
  WsToolResultMessage,
  WsScoreMessage,
  WsStatusMessage,
  WsErrorMessage,
} from '@/types';
import { api } from '@/services/api';
import { useNotificationStore } from '@/stores/notificationStore';
import { generateId } from '@/lib/utils';

function buildWsUrl(sessionId: string): string {
  const apiBase = import.meta.env.VITE_API_BASE_URL as string | undefined;

  if (apiBase) {
    const wsBase = apiBase.replace(/^http/, 'ws');
    return `${wsBase}/ws/session/${sessionId}`;
  }

  // Derive from current window location
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/session/${sessionId}`;
}

interface SessionStore {
  currentSession: Session | null;
  messages: Message[];
  toolCalls: ToolCall[];
  scores: SessionScore[];
  isConnected: boolean;
  isProcessing: boolean;
  error: string | null;

  // Actions
  createSession: (config: CreateSessionRequest) => Promise<void>;
  sendMessage: (content: string) => void;
  endSession: () => Promise<void>;
  connectWebSocket: (sessionId: string) => void;
  disconnectWebSocket: () => void;
  resetSession: () => void;
}

// WebSocket reference kept outside Zustand state to avoid serialization issues
let wsRef: WebSocket | null = null;

export const useSessionStore = create<SessionStore>((set, get) => ({
  currentSession: null,
  messages: [],
  toolCalls: [],
  scores: [],
  isConnected: false,
  isProcessing: false,
  error: null,

  createSession: async (config: CreateSessionRequest) => {
    set({ error: null });
    try {
      const session = await api.createSession(config);
      set({ currentSession: session, messages: [], toolCalls: [], scores: [] });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create session';
      set({ error: message });
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Session Creation Failed',
        message,
      });
    }
  },

  sendMessage: (content: string) => {
    const { currentSession } = get();
    if (!currentSession || !wsRef || wsRef.readyState !== WebSocket.OPEN) return;

    const userMessage: Message = {
      id: generateId(),
      sender: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isProcessing: true,
    }));

    wsRef.send(JSON.stringify({ type: 'message', data: { content } }));
  },

  endSession: async () => {
    const { currentSession } = get();
    if (!currentSession) return;

    try {
      if (wsRef && wsRef.readyState === WebSocket.OPEN) {
        wsRef.send(JSON.stringify({ type: 'end_session' }));
      }
      const updatedSession = await api.endSession(currentSession.id);
      set({ currentSession: updatedSession });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to end session';
      set({ error: message });
    }
  },

  connectWebSocket: (sessionId: string) => {
    // Close existing connection if any
    if (wsRef) {
      wsRef.close();
      wsRef = null;
    }

    const url = buildWsUrl(sessionId);
    const ws = new WebSocket(url);
    wsRef = ws;

    ws.onopen = () => {
      set({ isConnected: true, error: null });
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const envelope = JSON.parse(event.data as string) as WsEnvelope;
        handleWsMessage(envelope, set, get);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      set({ isConnected: false });
      const session = get().currentSession;
      if (session && session.status === 'active') {
        set({ error: 'Connection lost. Click reconnect to resume.' });
      }
    };

    ws.onerror = () => {
      set({ error: 'WebSocket connection error' });
    };
  },

  disconnectWebSocket: () => {
    if (wsRef) {
      wsRef.close();
      wsRef = null;
    }
    set({ isConnected: false });
  },

  resetSession: () => {
    if (wsRef) {
      wsRef.close();
      wsRef = null;
    }
    set({
      currentSession: null,
      messages: [],
      toolCalls: [],
      scores: [],
      isConnected: false,
      isProcessing: false,
      error: null,
    });
  },
}));

function handleWsMessage(
  envelope: WsEnvelope,
  set: (partial: Partial<SessionStore> | ((state: SessionStore) => Partial<SessionStore>)) => void,
  get: () => SessionStore,
) {
  switch (envelope.type) {
    case 'message_chunk': {
      const chunk = envelope as unknown as WsMessageChunk;
      set((state) => {
        const messages = [...state.messages];
        const lastMsg = messages[messages.length - 1];

        if (lastMsg && lastMsg.sender === 'agent' && lastMsg.id.startsWith('streaming-')) {
          // Append to existing streaming message
          messages[messages.length - 1] = {
            ...lastMsg,
            content: lastMsg.content + chunk.data.content,
          };
        } else {
          // Create new streaming message
          messages.push({
            id: `streaming-${chunk.data.message_id}`,
            sender: envelope.sender ?? 'agent',
            content: chunk.data.content,
            timestamp: envelope.timestamp,
          });
        }

        return { messages };
      });
      break;
    }

    case 'message_complete': {
      const complete = envelope as unknown as WsMessageComplete;
      set((state) => {
        const messages = [...state.messages];
        const streamingIdx = messages.findIndex(
          (m) => m.id === `streaming-${complete.data.message_id}`,
        );

        const finalMessage: Message = {
          id: complete.data.message_id,
          sender: envelope.sender ?? 'agent',
          content: complete.data.content,
          timestamp: envelope.timestamp,
          tool_calls: complete.data.tool_calls,
        };

        if (streamingIdx >= 0) {
          messages[streamingIdx] = finalMessage;
        } else {
          messages.push(finalMessage);
        }

        // Add any tool calls from the completed message, tagging each with message_id.
        // Skip tool calls that were already added via individual tool_call envelopes
        // during the agentic loop (matched by id).
        let toolCalls = state.toolCalls;
        if (complete.data.tool_calls && complete.data.tool_calls.length > 0) {
          const existingIds = new Set(toolCalls.map((tc) => tc.id));
          const newToolCalls = complete.data.tool_calls
            .filter((tc) => !existingIds.has(tc.id))
            .map((tc) => ({
              ...tc,
              message_id: complete.data.message_id,
              status: tc.status ?? ('completed' as const),
            }));
          if (newToolCalls.length > 0) {
            toolCalls = [...toolCalls, ...newToolCalls];
          }
        }

        return { messages, toolCalls, isProcessing: false };
      });
      break;
    }

    case 'tool_call': {
      const toolMsg = envelope as unknown as WsToolCallMessage;
      set((state) => ({
        toolCalls: [...state.toolCalls, { ...toolMsg.data, status: toolMsg.data.status ?? 'pending' }],
      }));
      break;
    }

    case 'tool_executing': {
      const execMsg = envelope as unknown as WsToolExecutingMessage;
      set((state) => ({
        toolCalls: state.toolCalls.map((tc) =>
          tc.id === execMsg.data.tool_call_id ? { ...tc, status: 'executing' as const } : tc,
        ),
      }));
      break;
    }

    case 'tool_result': {
      const resultMsg = envelope as unknown as WsToolResultMessage;
      set((state) => ({
        toolCalls: state.toolCalls.map((tc) =>
          tc.id === resultMsg.data.tool_call_id
            ? {
                ...tc,
                status: resultMsg.data.is_error ? ('error' as const) : ('completed' as const),
                result: resultMsg.data.result,
                duration_ms: resultMsg.data.duration_ms,
              }
            : tc,
        ),
      }));
      break;
    }

    case 'score': {
      const scoreMsg = envelope as unknown as WsScoreMessage;
      set((state) => ({
        scores: [...state.scores, scoreMsg.data],
      }));
      break;
    }

    case 'status': {
      const statusMsg = envelope as unknown as WsStatusMessage;
      const session = get().currentSession;
      if (session) {
        set({
          currentSession: { ...session, status: statusMsg.data.status },
        });
      }
      break;
    }

    case 'error': {
      const errorMsg = envelope as unknown as WsErrorMessage;
      const errText = errorMsg.data.message;
      const shortMsg = errText.length > 120 ? errText.slice(0, 120) + '...' : errText;
      set({ error: errText, isProcessing: false });
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Session Error',
        message: shortMsg,
        details: errText,
      });
      break;
    }
  }
}
