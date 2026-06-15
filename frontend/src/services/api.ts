import type {
  PaginatedResponse,
  ApiError,
  AggregateMetrics,
  Artifact,
  Evaluation,
  CreateEvaluationRequest,
  Dataset,
  DatasetDetail,
  CreateDatasetRequest,
  AnalyzeResponse,
  ImportRequest,
  Result,
  ComparisonResponse,
  ArenaLeaderboardResponse,
  Session,
  CreateSessionRequest,
  SendMessageRequest,
  Judge,
  CreateJudgeRequest,
  JudgePreset,
  Provider,
  CreateProviderRequest,
  UpdateProviderRequest,
  Rubric,
  CreateRubricRequest,
  UpdateRubricRequest,
  ImportRubricRequest,
  GenerateRubricRequest,
  RefineRubricRequest,
  ToolServer,
  CreateToolServerRequest,
  UpdateToolServerRequest,
  Harness,
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

  // --- Smart Import ---
  analyzeDatasetFiles: async (files: File[]): Promise<AnalyzeResponse> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const url = `${BASE_URL}/api/v1/datasets/analyze`;
    const response = await fetch(url, { method: 'POST', body: formData });
    if (!response.ok) {
      const errorBody = (await response.json().catch(() => ({
        type: 'about:blank',
        title: 'Analysis failed',
        status: response.status,
        detail: response.statusText,
        instance: url,
      }))) as ApiError;
      throw new ApiClientError(response.status, errorBody);
    }
    return response.json() as Promise<AnalyzeResponse>;
  },
  importDataset: (data: ImportRequest) =>
    request<Dataset>('/api/v1/datasets/import', { method: 'POST', body: JSON.stringify(data) }),

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
  listArtifacts: (evaluationId: string) =>
    request<Artifact[]>(`/api/v1/artifacts?evaluation_id=${encodeURIComponent(evaluationId)}`),
  getArtifact: (artifactId: string) => request<Artifact>(`/api/v1/artifacts/${artifactId}`),
  getArtifactDownloadUrl: (artifactId: string): string =>
    `${BASE_URL}/api/v1/artifacts/${artifactId}/download`,
  previewArtifact: async (artifactId: string): Promise<string> => {
    const url = `${BASE_URL}/api/v1/artifacts/${artifactId}/preview`;
    const response = await fetch(url);
    if (!response.ok) {
      const errorBody = (await response.json().catch(() => ({
        type: 'about:blank',
        title: 'Preview failed',
        status: response.status,
        detail: response.statusText,
        instance: url,
      }))) as ApiError;
      throw new ApiClientError(response.status, errorBody);
    }
    return response.text();
  },
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

export { ApiClientError };
export type { ApiError };
