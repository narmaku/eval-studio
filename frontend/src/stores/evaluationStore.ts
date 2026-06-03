import { create } from 'zustand';
import type {
  Evaluation,
  CreateEvaluationRequest,
  LogEntry,
  RunningEvaluation,
  WebSocketMessage,
} from '@/types';
import { api } from '@/services/api';

const POLL_INTERVAL_MS = 2000;
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

  setEvaluations: (evaluations: Evaluation[]) => void;
  setCurrentEvaluation: (evaluation: Evaluation | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  fetchEvaluations: (params?: { mode?: string; status?: string }) => Promise<void>;
  createAndRunEvaluation: (request: CreateEvaluationRequest) => Promise<Evaluation>;
  pollEvaluation: (id: string, onComplete: () => void) => () => void;

  // WebSocket-based methods
  connectToEvaluation: (evaluationId: string) => void;
  disconnectFromEvaluation: () => void;
  clearLogs: () => void;

  // sessionStorage persistence
  persistRunningEvaluation: (eval_: RunningEvaluation) => void;
  clearRunningEvaluation: () => void;
  getRunningEvaluation: () => RunningEvaluation | null;
}

function getWsUrl(evaluationId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? '';
  if (baseUrl) {
    // Convert http(s) base URL to ws(s)
    const wsBase = baseUrl.replace(/^http/, 'ws');
    return `${wsBase}/ws/progress/${evaluationId}`;
  }
  return `${protocol}//${window.location.host}/ws/progress/${evaluationId}`;
}

export const useEvaluationStore = create<EvaluationStore>((set, get) => ({
  evaluations: [],
  currentEvaluation: null,
  isLoading: false,
  error: null,
  logs: [],
  progress: null,
  wsConnection: null,

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

  createAndRunEvaluation: async (request: CreateEvaluationRequest) => {
    set({ isLoading: true, error: null });
    try {
      const evaluation = await api.createEvaluation(request);
      const runningEvaluation = await api.rerunEvaluation(evaluation.id);
      set({ currentEvaluation: runningEvaluation, isLoading: false });

      // Persist to sessionStorage
      get().persistRunningEvaluation({
        id: runningEvaluation.id,
        name: runningEvaluation.name,
        mode: runningEvaluation.mode,
      });

      return runningEvaluation;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create evaluation';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  pollEvaluation: (id: string, onComplete: () => void) => {
    const intervalId = setInterval(async () => {
      try {
        const evaluation = await api.getEvaluation(id);
        set({ currentEvaluation: evaluation });
        if (
          evaluation.status === 'completed' ||
          evaluation.status === 'failed' ||
          evaluation.status === 'cancelled'
        ) {
          clearInterval(intervalId);
          get().clearRunningEvaluation();
          onComplete();
        }
      } catch {
        // Silently ignore polling errors
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  },

  connectToEvaluation: (evaluationId: string) => {
    // Close existing connection if any
    const existing = get().wsConnection;
    if (existing) {
      existing.close();
    }

    // Reset logs and progress
    set({ logs: [], progress: null });

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
            logs: [...state.logs, data],
          }));
        } else if (data.type === 'status') {
          const currentEval = get().currentEvaluation;
          if (currentEval) {
            set({ currentEvaluation: { ...currentEval, status: data.status } });
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
      // Check evaluation status via API when connection closes
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
          }
        })
        .catch(() => {
          // Ignore errors on status check
        });
    };

    set({ wsConnection: ws });
  },

  disconnectFromEvaluation: () => {
    const ws = get().wsConnection;
    if (ws) {
      ws.close();
    }
    set({ wsConnection: null });
  },

  clearLogs: () => set({ logs: [], progress: null }),

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
