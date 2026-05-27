// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export type EvaluationMode = 'qa' | 'agent' | 'rag' | 'arena';
export type EvaluationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Evaluation {
  id: string;
  name: string;
  mode: EvaluationMode;
  status: EvaluationStatus;
  dataset_id: string | null;
  environment_id: string | null;
  judge_config_id: string | null;
  config: EvaluationConfig;
  result_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface RAGEndpointSettings {
  backend_type: 'http' | 'pgvector';
  // HTTP fields
  endpoint_url?: string;
  auth_header?: string;
  query_field?: string;
  answer_field?: string;
  chunks_field?: string;
  // pgvector fields
  connection_string?: string;
  table_name?: string;
  embedding_column?: string;
  content_column?: string;
  top_k?: number;
  generator_provider_id?: string;
  embedding_model?: string;
}

export interface EvaluationConfig {
  model_endpoint: ModelEndpoint;
  judge_config: JudgeReference;
  max_turns?: number;
  scenario_id?: string;
  environment_id?: string;
  contestants?: ModelEndpoint[]; // arena mode
  rag_endpoint?: RAGEndpointSettings; // rag mode
  rag_metrics?: string[]; // rag mode
}

export interface ModelEndpoint {
  provider_id?: string;
  name: string;
  litellm_model: string;
  api_base?: string;
  api_key_env?: string;
  tags?: string[];
}

export interface Provider {
  id: string;
  name: string;
  litellm_model: string;
  api_base: string | null;
  has_api_key: boolean;
  proxy: string | null;
  tags: string[];
  purpose: string;
}

export interface ProviderModel {
  id: string;
  owned_by: string;
}

export interface JudgeReference {
  judge_id?: string;
  preset?: string;
  provider_id?: string;
}

export interface CreateEvaluationRequest {
  name: string;
  mode: EvaluationMode;
  dataset_id?: string;
  judge_config_id?: string;
  config: EvaluationConfig;
}
