import type { components } from './generated/api';

export type RubricDimension = components['schemas']['RubricDimension'];
export type Rubric = components['schemas']['RubricResponse'];
export type ImportRubricRequest = components['schemas']['RubricImportRequest'];
export type GenerateRubricRequest = components['schemas']['RubricGenerateRequest'];
export type RefineRubricRequest = components['schemas']['RubricRefineRequest'];

export interface CreateRubricRequest {
  name: string;
  description?: string | null;
  dimensions: RubricDimension[];
  pass_threshold?: number;
  aggregation?: string;
  prompt_template?: string | null;
}

export type UpdateRubricRequest = Partial<CreateRubricRequest>;
