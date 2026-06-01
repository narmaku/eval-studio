// Types aligned with backend DatasetResponse / DatasetDetailResponse schemas.

export type DatasetFormat = 'qa_pairs' | 'jsonl' | 'csv';

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  format: string;
  version: string;
  tags: string[];
  source_type: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetItem {
  id: string;
  question: string;
  expected_answer: string | null;
  metadata: Record<string, unknown> | null;
  order_index: number;
}

export interface DatasetDetail extends Dataset {
  items: DatasetItem[];
}

export interface DatasetItemCreate {
  question: string;
  expected_answer?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateDatasetRequest {
  name: string;
  description?: string;
  format: DatasetFormat;
  version?: string;
  tags?: string[];
  items?: DatasetItemCreate[];
}

// --- Smart Import types (aligned with backend AnalyzeResponse / ImportRequest) ---

export interface FileAnalysisResult {
  filename: string;
  format: string;
  field_count: number;
  row_count: number;
  fields: string[];
  sample_rows: Record<string, unknown>[];
  errors: string[];
}

export interface SuggestedMapping {
  question_field: string | null;
  answer_field: string | null;
  metadata_fields: string[];
  confidence: number;
}

export interface AnalyzeResponse {
  analysis_id: string;
  files: FileAnalysisResult[];
  merged_fields: string[];
  suggested_mapping: SuggestedMapping;
  total_rows: number;
}

export interface FieldMapping {
  question_field: string;
  answer_field: string;
}

export type MergeMode = 'single' | 'separate';

export interface ImportRequest {
  analysis_id: string;
  name: string;
  description?: string;
  tags?: string[];
  mapping: FieldMapping;
  merge_mode: MergeMode;
}
