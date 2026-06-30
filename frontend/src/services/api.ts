import type {
  PaginatedResponse,
  ApiError,
  AggregateMetrics,
  Artifact,
  UpdateArtifactRequest,
  Evaluation,
  CreateEvaluationRequest,
  UpdateEvaluationRequest,
  Dataset,
  DatasetDetail,
  CreateDatasetRequest,
  AnalyzeResponse,
  ImportRequest,
  Result,
  UpdateResultRequest,
  ComparisonResponse,
  ArenaLeaderboardResponse,
  Session,
  CreateSessionRequest,
  UpdateSessionRequest,
  SendMessageRequest,
  Provider,
  CreateProviderRequest,
  UpdateProviderRequest,
  Rubric,
  CreateRubricRequest,
  UpdateRubricRequest,
  ImportRubricRequest,
  GenerateRubricRequest,
  RefineRubricRequest,
  EvaluatorInfo,
  ToolServer,
  CreateToolServerRequest,
  UpdateToolServerRequest,
  Harness,
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
const API_KEY_STORAGE_KEY = 'eval-studio-api-key';

export function getStoredApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE_KEY);
}

export function setStoredApiKey(key: string | null): void {
  if (key) {
    localStorage.setItem(API_KEY_STORAGE_KEY, key);
  } else {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  }
}

function authHeaders(): Record<string, string> {
  const key = getStoredApiKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}

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

async function request<T>(
  path: string,
  options?: RequestInit & { parse?: 'json' | 'text' },
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const isFormData = options?.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...authHeaders(),
    ...(options?.headers as Record<string, string>),
  };
  const response = await fetch(url, { ...options, headers });

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

  if (response.status === 204) {
    return undefined as T;
  }

  if (options?.parse === 'text') {
    return response.text() as Promise<T>;
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
  updateEvaluation: (id: string, data: UpdateEvaluationRequest) =>
    request<Evaluation>(`/api/v1/evaluations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteEvaluation: (id: string) =>
    request<void>(`/api/v1/evaluations/${id}`, { method: 'DELETE' }),
  runEvaluation: (id: string) =>
    request<Evaluation>(`/api/v1/evaluations/${id}/run`, { method: 'POST' }),
  rerunEvaluation: (id: string) =>
    request<Evaluation>(`/api/v1/evaluations/${id}/rerun`, { method: 'POST' }),
  cancelEvaluation: (id: string) =>
    request<Evaluation>(`/api/v1/evaluations/${id}/cancel`, { method: 'POST' }),

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
  updateSession: (id: string, data: UpdateSessionRequest) =>
    request<Session>(`/api/v1/sessions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSession: (id: string) => request<void>(`/api/v1/sessions/${id}`, { method: 'DELETE' }),
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

  // --- Smart Import ---
  analyzeDatasetFiles: (files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return request<AnalyzeResponse>('/api/v1/datasets/analyze', { method: 'POST', body: formData });
  },
  importDataset: (data: ImportRequest) =>
    request<Dataset>('/api/v1/datasets/import', { method: 'POST', body: JSON.stringify(data) }),

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
  updateResult: (id: string, data: UpdateResultRequest) =>
    request<Result>(`/api/v1/results/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteResult: (id: string) => request<void>(`/api/v1/results/${id}`, { method: 'DELETE' }),
  getAggregateMetrics: (evaluationId: string) =>
    request<AggregateMetrics>(
      `/api/v1/results/aggregate?evaluation_id=${encodeURIComponent(evaluationId)}`,
    ),
  compareEvaluations: (evaluationIds: string[], referenceId?: string) => {
    const query = new URLSearchParams();
    evaluationIds.forEach((id) => query.append('evaluation_id', id));
    if (referenceId) query.set('reference_evaluation_id', referenceId);
    return request<ComparisonResponse>(`/api/v1/results/compare?${query.toString()}`);
  },
  getArenaLeaderboard: (evaluationId: string) =>
    request<ArenaLeaderboardResponse>(`/api/v1/results/arena/${evaluationId}`),

  // --- Providers ---
  listProviders: () => {
    return request<Provider[]>('/api/v1/providers');
  },
  getProvider: (id: string) => request<Provider>(`/api/v1/providers/${id}`),
  createProvider: (data: CreateProviderRequest) =>
    request<Provider>('/api/v1/providers', { method: 'POST', body: JSON.stringify(data) }),
  updateProvider: (id: string, data: UpdateProviderRequest) =>
    request<Provider>(`/api/v1/providers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProvider: (id: string) => request<void>(`/api/v1/providers/${id}`, { method: 'DELETE' }),
  listProviderModels: (providerId: string) =>
    request<{ id: string; owned_by: string }[]>(`/api/v1/providers/${providerId}/models`),
  testProviderConnection: (data: CreateProviderRequest) =>
    request<{ success: boolean; message: string; details?: string }>('/api/v1/providers/test', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // --- Rubrics ---
  listRubrics: (params?: { name?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.name) query.set('name', params.name);
    if (params?.page !== undefined) query.set('page', String(params.page));
    if (params?.page_size !== undefined) query.set('page_size', String(params.page_size));
    const qs = query.toString();
    return request<PaginatedResponse<Rubric>>(`/api/v1/rubrics${qs ? `?${qs}` : ''}`);
  },
  getRubric: (id: string) => request<Rubric>(`/api/v1/rubrics/${id}`),
  createRubric: (data: CreateRubricRequest) =>
    request<Rubric>('/api/v1/rubrics', { method: 'POST', body: JSON.stringify(data) }),
  updateRubric: (id: string, data: UpdateRubricRequest) =>
    request<Rubric>(`/api/v1/rubrics/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRubric: (id: string) => request<void>(`/api/v1/rubrics/${id}`, { method: 'DELETE' }),
  importRubric: (data: ImportRubricRequest) =>
    request<Rubric>('/api/v1/rubrics/import', { method: 'POST', body: JSON.stringify(data) }),
  generateRubric: (data: GenerateRubricRequest) =>
    request<Rubric>('/api/v1/rubrics/generate', { method: 'POST', body: JSON.stringify(data) }),
  refineRubric: (id: string, data: RefineRubricRequest) =>
    request<Rubric>(`/api/v1/rubrics/${id}/refine`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // --- Evaluators ---
  listEvaluators: (mode?: string) => {
    const query = new URLSearchParams();
    if (mode) query.set('mode', mode);
    const qs = query.toString();
    return request<EvaluatorInfo[]>(`/api/v1/evaluators${qs ? `?${qs}` : ''}`);
  },
  getEvaluator: (id: string) => request<EvaluatorInfo>(`/api/v1/evaluators/${id}`),

  // --- Evaluator Config Files ---
  listEvaluatorConfigFiles: (evaluatorId: string) =>
    request<{ filename: string; size: number; modified_at: string }[]>(
      `/api/v1/evaluators/${evaluatorId}/config-files`,
    ),
  uploadEvaluatorConfigFile: (evaluatorId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<{ filename: string; size: number }>(
      `/api/v1/evaluators/${evaluatorId}/config-files`,
      { method: 'POST', body: formData },
    );
  },
  deleteEvaluatorConfigFile: (evaluatorId: string, filename: string) =>
    request<void>(`/api/v1/evaluators/${evaluatorId}/config-files/${filename}`, {
      method: 'DELETE',
    }),
  getEvaluatorConfigFile: (evaluatorId: string, filename: string) =>
    request<string>(`/api/v1/evaluators/${evaluatorId}/config-files/${filename}`, {
      parse: 'text',
    }),

  // Tool Servers
  listToolServers: (params?: { type?: string; enabled?: boolean }) => {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set('type', params.type);
    if (params?.enabled !== undefined) searchParams.set('enabled', String(params.enabled));
    const query = searchParams.toString();
    return request<ToolServer[]>(`/api/v1/tool-servers${query ? `?${query}` : ''}`);
  },
  createToolServer: (data: CreateToolServerRequest) =>
    request<ToolServer>('/api/v1/tool-servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateToolServer: (id: string, data: UpdateToolServerRequest) =>
    request<ToolServer>(`/api/v1/tool-servers/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteToolServer: (id: string) =>
    request<void>(`/api/v1/tool-servers/${id}`, { method: 'DELETE' }),
  validateToolServer: (id: string) =>
    request<{ available: boolean; path: string | null }>(`/api/v1/tool-servers/${id}/validate`, {
      method: 'POST',
    }),

  // --- Artifacts ---
  listArtifacts: (evaluationId: string, page = 1, pageSize = 100) =>
    request<PaginatedResponse<Artifact>>(
      `/api/v1/artifacts?evaluation_id=${encodeURIComponent(evaluationId)}&page=${page}&page_size=${pageSize}`,
    ),
  getArtifact: (artifactId: string) => request<Artifact>(`/api/v1/artifacts/${artifactId}`),
  updateArtifact: (artifactId: string, data: UpdateArtifactRequest) =>
    request<Artifact>(`/api/v1/artifacts/${artifactId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  getArtifactDownloadUrl: (artifactId: string): string =>
    `${BASE_URL}/api/v1/artifacts/${artifactId}/download`,
  previewArtifact: (artifactId: string) =>
    request<string>(`/api/v1/artifacts/${artifactId}/preview`, { parse: 'text' }),
  deleteArtifact: (artifactId: string) =>
    request<void>(`/api/v1/artifacts/${artifactId}`, { method: 'DELETE' }),

  // --- Harnesses ---
  listHarnesses: (params?: { type?: string; enabled?: boolean }) => {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set('type', params.type);
    if (params?.enabled !== undefined) searchParams.set('enabled', String(params.enabled));
    const query = searchParams.toString();
    return request<Harness[]>(`/api/v1/harnesses${query ? `?${query}` : ''}`);
  },
  getHarness: (id: string) => request<Harness>(`/api/v1/harnesses/${id}`),
  checkHarness: (id: string) =>
    request<{ available: boolean; version: string | null }>(`/api/v1/harnesses/${id}/check`, {
      method: 'POST',
    }),
};

export function getWsAuthParam(): string {
  const key = getStoredApiKey();
  return key ? `?token=${encodeURIComponent(key)}` : '';
}

export { ApiClientError };
export type { ApiError };
