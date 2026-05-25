// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export type EvaluationMode = 'qa' | 'agent' | 'rag' | 'arena';
export type EvaluationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Evaluation {
  id: string;
  name: string;
  description: string;
  mode: EvaluationMode;
  status: EvaluationStatus;
  dataset_id: string | null;
  judge_id: string | null;
  config: EvaluationConfig;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface EvaluationConfig {
  model_endpoint: ModelEndpoint;
  judge_config: JudgeReference;
  max_turns?: number;
  scenario_id?: string;
  environment_id?: string;
  contestants?: ModelEndpoint[]; // arena mode
}

export interface ModelEndpoint {
  name: string;
  litellm_model: string;
  api_base?: string;
  api_key_env?: string;
  tags?: string[];
}

export interface JudgeReference {
  judge_id?: string;
  preset?: string;
}

export interface CreateEvaluationRequest {
  name: string;
  description?: string;
  mode: EvaluationMode;
  dataset_id?: string;
  judge_id?: string;
  config: EvaluationConfig;
}
