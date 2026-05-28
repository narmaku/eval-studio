export interface RubricDimension {
  name: string;
  weight: number;
  description: string;
}

export interface Rubric {
  id: string;
  name: string;
  description: string | null;
  dimensions: RubricDimension[];
  pass_threshold: number;
  aggregation: string;
  prompt_template: string | null;
  created_at: string;
  updated_at: string;
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
