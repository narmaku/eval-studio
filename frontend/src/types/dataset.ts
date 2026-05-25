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
  expected_answer: string;
  metadata: Record<string, unknown>;
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
