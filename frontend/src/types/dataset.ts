// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export type DatasetFormat = 'qa_pairs' | 'jsonl' | 'csv' | 'huggingface';
export type DatasetSourceType = 'upload' | 'git' | 's3' | 'url' | 'huggingface';

export interface Dataset {
  id: string;
  name: string;
  description: string;
  format: DatasetFormat;
  version: string;
  tags: string[];
  source: DatasetSource;
  stats: DatasetStats;
  created_at: string;
  updated_at: string;
}

export interface DatasetSource {
  type: DatasetSourceType;
  original_format: string;
  imported_at: string;
}

export interface DatasetStats {
  item_count: number;
  categories: string[];
  avg_question_length: number;
  avg_answer_length: number;
}

export interface DatasetItem {
  id: string;
  question: string;
  expected_answer: string;
  metadata: Record<string, unknown>;
}

export interface CreateDatasetRequest {
  name: string;
  description?: string;
  format: DatasetFormat;
  tags?: string[];
}
