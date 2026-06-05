// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.
//
// TODO: Judge types have significant structural differences from backend schemas.
// Backend JudgeConfigResponse uses flat fields (model, temperature, dimensions as
// list[dict[str, Any]]) while frontend models a panel of members with weights and
// typed dimensions. Needs a coordinated redesign.
// See https://github.com/narmaku/eval-studio/issues/106.

export type AggregationStrategy = 'majority_vote' | 'average' | 'max' | 'weighted_average';

export interface Judge {
  id: string;
  name: string;
  is_preset: boolean;
  panel: JudgePanelMember[];
  aggregation: AggregationStrategy;
  prompt_template: string;
  pass_threshold: number;
  dimensions: JudgeDimension[];
  created_at: string;
  updated_at: string;
}

export interface JudgePanelMember {
  model: string;
  temperature: number;
  weight: number;
}

export interface JudgeDimension {
  name: string;
  weight: number;
}

export interface JudgePreset {
  id: string;
  name: string;
  description: string;
  judge: Judge;
}

export interface CreateJudgeRequest {
  name: string;
  panel: JudgePanelMember[];
  aggregation: AggregationStrategy;
  prompt_template: string;
  pass_threshold: number;
  dimensions: JudgeDimension[];
}
