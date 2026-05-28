import type {
  PaginatedResponse,
  ApiError,
  Evaluation,
  CreateEvaluationRequest,
  Dataset,
  DatasetDetail,
  CreateDatasetRequest,
  Result,
  ResultComparison,
  Session,
  CreateSessionRequest,
  SendMessageRequest,
  Environment,
  CreateEnvironmentRequest,
  HealthCheckResult,
  Judge,
  CreateJudgeRequest,
  JudgePreset,
  Provider,
  Rubric,
  CreateRubricRequest,
  UpdateRubricRequest,
  EvaluatorInfo,
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

class ApiClientError extends Error {
  status: number;
  detail: ApiError;

  constructor(status: number, detail: ApiError) {
    super(detail.detail);
    this.name = 'ApiClientError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => ({
      type: 'about:blank',
      title: 'Request failed',
      status: response.status,
      detail: response.statusText,
      instance: path,
    }))) as ApiError;
    throw new ApiClientError(response.status, errorBody);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  // --- Health ---
  getHealth: () => request<{ status: string }>('/api/v1/health'),

  // --- Evaluations ---
  listEvaluations: (params?: {
    mode?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.mode) query.set('mode', params.mode);
    if (params?.status) query.set('status', params.status);
    if (params?.page) query.set('page', String(params.page));
    if (params?.page_size) query.set('page_size', String(params.page_size));
    const qs = query.toString();
    return request<PaginatedResponse<Evaluation>>(`/api/v1/evaluations${qs ? `?${qs}` : ''}`);
  },
  getEvaluation: (id: string) => request<Evaluation>(`/api/v1/evaluations/${id}`),
  createEvaluation: (data: CreateEvaluationRequest) =>
    request<Evaluation>('/api/v1/evaluations', { method: 'POST', body: JSON.stringify(data) }),
  deleteEvaluation: (id: string) =>
    request<void>(`/api/v1/evaluations/${id}`, { method: 'DELETE' }),
  rerunEvaluation: (id: string) =>
    request<Evaluation>(`/api/v1/evaluations/${id}/rerun`, { method: 'POST' }),

  // --- Sessions ---
  listSessions: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    evaluation_id?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', String(params.page));
    if (params?.page_size) query.set('page_size', String(params.page_size));
    if (params?.status) query.set('status', params.status);
    if (params?.evaluation_id) query.set('evaluation_id', params.evaluation_id);
    const qs = query.toString();
    return request<PaginatedResponse<Session>>(`/api/v1/sessions${qs ? `?${qs}` : ''}`);
  },
  createSession: (data: CreateSessionRequest) =>
    request<Session>('/api/v1/sessions', { method: 'POST', body: JSON.stringify(data) }),
  getSession: (id: string) => request<Session>(`/api/v1/sessions/${id}`),
  sendMessage: (sessionId: string, data: SendMessageRequest) =>
    request<Session>(`/api/v1/sessions/${sessionId}/message`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  endSession: (id: string) => request<Session>(`/api/v1/sessions/${id}/end`, { method: 'POST' }),
  scoreSession: (id: string, judgeConfig: Record<string, unknown>) =>
    request<Session>(`/api/v1/sessions/${id}/score`, {
      method: 'POST',
      body: JSON.stringify({ judge_config: judgeConfig }),
    }),
  getSessionReplay: (id: string) => request<Session>(`/api/v1/sessions/${id}/replay`),

  // --- Datasets ---
  listDatasets: (params?: { page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', String(params.page));
    if (params?.page_size) query.set('page_size', String(params.page_size));
    const qs = query.toString();
    return request<PaginatedResponse<Dataset>>(`/api/v1/datasets${qs ? `?${qs}` : ''}`);
  },
  getDataset: (id: string) => request<DatasetDetail>(`/api/v1/datasets/${id}`),
  createDataset: (data: CreateDatasetRequest) =>
    request<Dataset>('/api/v1/datasets', { method: 'POST', body: JSON.stringify(data) }),
  updateDataset: (id: string, data: Partial<CreateDatasetRequest>) =>
    request<Dataset>(`/api/v1/datasets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteDataset: (id: string) => request<void>(`/api/v1/datasets/${id}`, { method: 'DELETE' }),

  // --- Environments ---
  listEnvironments: () => request<Environment[]>('/api/v1/environments'),
  getEnvironment: (id: string) => request<Environment>(`/api/v1/environments/${id}`),
  createEnvironment: (data: CreateEnvironmentRequest) =>
    request<Environment>('/api/v1/environments', { method: 'POST', body: JSON.stringify(data) }),
  provisionEnvironment: (id: string) =>
    request<Environment>(`/api/v1/environments/${id}/provision`, { method: 'POST' }),
  teardownEnvironment: (id: string) =>
    request<void>(`/api/v1/environments/${id}/teardown`, { method: 'POST' }),
  getEnvironmentHealth: (id: string) =>
    request<HealthCheckResult>(`/api/v1/environments/${id}/health`),

  // --- Judges ---
  listJudges: () => request<Judge[]>('/api/v1/judges'),
  getJudge: (id: string) => request<Judge>(`/api/v1/judges/${id}`),
  createJudge: (data: CreateJudgeRequest) =>
    request<Judge>('/api/v1/judges', { method: 'POST', body: JSON.stringify(data) }),
  updateJudge: (id: string, data: Partial<CreateJudgeRequest>) =>
    request<Judge>(`/api/v1/judges/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  listJudgePresets: () => request<JudgePreset[]>('/api/v1/judges/presets'),

  // --- Results ---
  listResults: (params?: { evaluation_id?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.evaluation_id) query.set('evaluation_id', params.evaluation_id);
    if (params?.page) query.set('page', String(params.page));
    if (params?.page_size) query.set('page_size', String(params.page_size));
    const qs = query.toString();
    return request<PaginatedResponse<Result>>(`/api/v1/results${qs ? `?${qs}` : ''}`);
  },
  getResult: (id: string) => request<Result>(`/api/v1/results/${id}`),
  compareResults: (evaluationIds: string[]) => {
    const query = new URLSearchParams();
    evaluationIds.forEach((id) => query.append('evaluation_id', id));
    return request<ResultComparison>(`/api/v1/results/compare?${query.toString()}`);
  },

  // --- Providers ---
  listProviders: (purpose?: string) => {
    const query = new URLSearchParams();
    if (purpose) query.set('purpose', purpose);
    const qs = query.toString();
    return request<Provider[]>(`/api/v1/providers${qs ? `?${qs}` : ''}`);
  },
  getProvider: (id: string) => request<Provider>(`/api/v1/providers/${id}`),
  listProviderModels: (providerId: string) =>
    request<{ id: string; owned_by: string }[]>(`/api/v1/providers/${providerId}/models`),

  // --- Rubrics ---
  listRubrics: (params?: { name?: string; offset?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.name) query.set('name', params.name);
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const qs = query.toString();
    return request<Rubric[]>(`/api/v1/rubrics${qs ? `?${qs}` : ''}`);
  },
  getRubric: (id: string) => request<Rubric>(`/api/v1/rubrics/${id}`),
  createRubric: (data: CreateRubricRequest) =>
    request<Rubric>('/api/v1/rubrics', { method: 'POST', body: JSON.stringify(data) }),
  updateRubric: (id: string, data: UpdateRubricRequest) =>
    request<Rubric>(`/api/v1/rubrics/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRubric: (id: string) => request<void>(`/api/v1/rubrics/${id}`, { method: 'DELETE' }),

  // --- Evaluators ---
  listEvaluators: (mode?: string) => {
    const query = new URLSearchParams();
    if (mode) query.set('mode', mode);
    const qs = query.toString();
    return request<EvaluatorInfo[]>(`/api/v1/evaluators${qs ? `?${qs}` : ''}`);
  },
  getEvaluator: (id: string) => request<EvaluatorInfo>(`/api/v1/evaluators/${id}`),

  // --- Adapters & Config ---
  listAdapters: () => request<{ name: string; modes: string[] }[]>('/api/v1/adapters'),
  getConfig: () => request<Record<string, unknown>>('/api/v1/config'),
};

export { ApiClientError };
export type { ApiError };
