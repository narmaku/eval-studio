import type { components } from './generated/api';

export type RubricCriterion = components['schemas']['RubricCriterion'];
export type RubricDimension = components['schemas']['RubricDimension'];
export type Rubric = components['schemas']['RubricResponse'];
export type GenerateRubricRequest = components['schemas']['RubricGenerateRequest'];
export type RefineRubricRequest = components['schemas']['RubricRefineRequest'];

export interface ImportRubricRequest {
  yaml_content: string;
  name?: string;
  description?: string;
  tags?: string[];
  metric_id?: string;
}

export interface CreateRubricRequest {
  name: string;
  description?: string | null;
  dimensions: RubricDimension[];
  pass_threshold?: number;
  aggregation?: string;
  prompt_template?: string | null;
}

export type UpdateRubricRequest = Partial<CreateRubricRequest>;

export interface CriterionPreview {
  name: string;
  criterion: string;
}

export interface DimensionPreview {
  name: string;
  description: string;
  weight: number;
  criteria_count: number;
  criteria: CriterionPreview[];
}

export interface DetectedMetric {
  metric_id: string | null;
  suggested_name: string;
  suggested_description: string | null;
  dimensions_preview: DimensionPreview[];
  criteria_count: number;
  pass_threshold: number | null;
}

export interface RubricAnalyzeRequest {
  yaml_content: string;
}

export interface RubricAnalyzeResponse {
  detected_format: string;
  metrics: DetectedMetric[];
}
