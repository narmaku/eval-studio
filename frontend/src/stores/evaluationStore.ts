import { create } from 'zustand';
import type {
  Evaluation,
  CreateEvaluationRequest,
  UpdateEvaluationRequest,
  LogEntry,
  RunningEvaluation,
  WebSocketMessage,
} from '@/types';
import { api, getWsAuthParam } from '@/services/api';

const MAX_LOGS = 500;
const RUNNING_EVAL_KEY = 'runningEvaluation';

interface EvaluationProgress {
  completed: number;
  total: number;
  currentItem: string;
  contestantModel?: string;
}

interface EvaluationStore {
  evaluations: Evaluation[];
  currentEvaluation: Evaluation | null;
  isLoading: boolean;
  error: string | null;
  logs: LogEntry[];
  progress: EvaluationProgress | null;
  wsConnection: WebSocket | null;
  _connectedEvaluationId: string | null;
  _reconnectTimer: ReturnType<typeof setTimeout> | null;

  setEvaluations: (evaluations: Evaluation[]) => void;
  setCurrentEvaluation: (evaluation: Evaluation | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchEvaluations: (params?: { mode?: string; status?: string }) => Promise<void>;
  updateEvaluation: (id: string, data: UpdateEvaluationRequest) => Promise<Evaluation>;
  deleteEvaluation: (id: string) => Promise<void>;
  createAndRunEvaluation: (request: CreateEvaluationRequest) => Promise<Evaluation>;
  // WebSocket-based methods
  connectToEvaluation: (evaluationId: string) => void;
  disconnectFromEvaluation: () => void;
  clearLogs: () => void;
  resumeTracking: () => void;

  // sessionStorage persistence
  persistRunningEvaluation: (eval_: RunningEvaluation) => void;
  clearRunningEvaluation: () => void;
  getRunningEvaluation: () => RunningEvaluation | null;
}

function getWsUrl(evaluationId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? '';
  const auth = getWsAuthParam();
  if (baseUrl) {
    const wsBase = baseUrl.replace(/^http/, 'ws');
    return `${wsBase}/ws/progress/${evaluationId}${auth}`;
  }
  return `${protocol}//${window.location.host}/ws/progress/${evaluationId}${auth}`;
}

export const useEvaluationStore = create<EvaluationStore>((set, get) => ({
  evaluations: [],
  currentEvaluation: null,
  isLoading: false,
  error: null,
  logs: [],
  progress: null,
  wsConnection: null,
  _connectedEvaluationId: null,
  _reconnectTimer: null,

  setEvaluations: (evaluations) => set({ evaluations }),
  setCurrentEvaluation: (currentEvaluation) => set({ currentEvaluation }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  fetchEvaluations: async (params?: { mode?: string; status?: string }) => {
    set({ isLoading: true, error: null });
    try {
      const queryParams: { mode?: string; status?: string } = {};
      if (params?.mode) {
        queryParams.mode = params.mode;
      }
      if (params?.status) {
        queryParams.status = params.status;
      }
      const response = await api.listEvaluations(queryParams);
      set({ evaluations: response.items, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch evaluations';
      set({ error: message, isLoading: false });
    }
  },

  updateEvaluation: async (id: string, data: UpdateEvaluationRequest) => {
    set({ error: null });
    try {
      const updated = await api.updateEvaluation(id, data);
      set((state) => ({
        evaluations: state.evaluations.map((e) => (e.id === id ? updated : e)),
        currentEvaluation: state.currentEvaluation?.id === id ? updated : state.currentEvaluation,
      }));
      return updated;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update evaluation';
      set({ error: message });
      throw err;
    }
  },

  deleteEvaluation: async (id: string) => {
    set({ error: null });
    try {
      await api.deleteEvaluation(id);
      set((state) => ({
        evaluations: state.evaluations.filter((e) => e.id !== id),
        currentEvaluation: state.currentEvaluation?.id === id ? null : state.currentEvaluation,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete evaluation';
      set({ error: message });
      throw err;
    }
  },

  createAndRunEvaluation: async (request: CreateEvaluationRequest) => {
    set({ isLoading: true, error: null });
    try {
      const evaluation = await api.createEvaluation(request);
      set({ currentEvaluation: evaluation, isLoading: false });

      get().persistRunningEvaluation({
        id: evaluation.id,
        name: evaluation.name,
        mode: evaluation.mode,
      });

      const runningEvaluation = await api.runEvaluation(evaluation.id);
      set({ currentEvaluation: runningEvaluation });

      // WS connects after run — replay buffer ensures no messages are lost
      get().connectToEvaluation(evaluation.id);

      return runningEvaluation;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create evaluation';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  connectToEvaluation: (evaluationId: string) => {
    // Skip if already connected (or connecting) to this evaluation
    const existing = get().wsConnection;
    if (
      existing &&
      (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING) &&
      get()._connectedEvaluationId === evaluationId
    ) {
      return;
    }

    // Cancel any pending reconnect timer
    const timer = get()._reconnectTimer;
    if (timer) clearTimeout(timer);

    // Close existing connection if any — clear ID first so onclose guard skips
    if (existing) {
      set({ _connectedEvaluationId: null });
      existing.close();
    }

    // Reset logs and progress
    set({ logs: [], progress: null, _connectedEvaluationId: evaluationId, _reconnectTimer: null });

    const wsUrl = getWsUrl(evaluationId);
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as WebSocketMessage;

        if (data.type === 'progress') {
          set({
            progress: {
              completed: data.completed,
              total: data.total,
              currentItem: data.current_item,
              contestantModel: data.contestant_model,
            },
          });
        } else if (data.type === 'log') {
          set((state) => ({
            logs: [...state.logs.slice(-(MAX_LOGS - 1)), data],
          }));
        } else if (data.type === 'status') {
          const currentEval = get().currentEvaluation;
          if (currentEval) {
            set({
              currentEvaluation: {
                ...currentEval,
                status: data.status,
                error: data.error ?? currentEval.error,
              },
            });
          }
          if (
            data.status === 'completed' ||
            data.status === 'failed' ||
            data.status === 'cancelled'
          ) {
            get().clearRunningEvaluation();
          }
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      // Only process if this is still the connection we're tracking
      if (get()._connectedEvaluationId !== evaluationId) return;

      set({ wsConnection: null, _connectedEvaluationId: null });

      void api
        .getEvaluation(evaluationId)
        .then((evaluation) => {
          set({ currentEvaluation: evaluation });
          if (
            evaluation.status === 'completed' ||
            evaluation.status === 'failed' ||
            evaluation.status === 'cancelled'
          ) {
            get().clearRunningEvaluation();
          } else {
            // Still running — reconnect after delay
            const running = get().getRunningEvaluation();
            if (running && running.id === evaluationId) {
              const timer = setTimeout(() => get().connectToEvaluation(evaluationId), 3000);
              set({ _reconnectTimer: timer });
            }
          }
        })
        .catch(() => {
          // API unreachable — retry reconnect after longer delay
          const running = get().getRunningEvaluation();
          if (running && running.id === evaluationId) {
            const timer = setTimeout(() => get().connectToEvaluation(evaluationId), 5000);
            set({ _reconnectTimer: timer });
          }
        });
    };

    set({ wsConnection: ws });
  },

  disconnectFromEvaluation: () => {
    const timer = get()._reconnectTimer;
    if (timer) clearTimeout(timer);

    const ws = get().wsConnection;
    // Clear state BEFORE closing so the onclose guard skips reconnection
    set({ wsConnection: null, _connectedEvaluationId: null, _reconnectTimer: null });
    if (ws) ws.close();
  },

  clearLogs: () => set({ logs: [], progress: null }),

  resumeTracking: () => {
    const running = get().getRunningEvaluation();
    if (!running) return;

    const ws = get().wsConnection;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    get().connectToEvaluation(running.id);
  },

  persistRunningEvaluation: (eval_: RunningEvaluation) => {
    try {
      sessionStorage.setItem(RUNNING_EVAL_KEY, JSON.stringify(eval_));
    } catch {
      // sessionStorage may be unavailable
    }
  },

  clearRunningEvaluation: () => {
    try {
      sessionStorage.removeItem(RUNNING_EVAL_KEY);
    } catch {
      // sessionStorage may be unavailable
    }
  },

  getRunningEvaluation: (): RunningEvaluation | null => {
    try {
      const stored = sessionStorage.getItem(RUNNING_EVAL_KEY);
      if (stored) {
        return JSON.parse(stored) as RunningEvaluation;
      }
    } catch {
      // sessionStorage may be unavailable or data may be corrupted
    }
    return null;
  },
}));
