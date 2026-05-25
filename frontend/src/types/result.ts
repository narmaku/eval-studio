// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export interface Result {
  id: string;
  evaluation_id: string;
  status: 'pending' | 'completed' | 'failed';
  scores: Score[];
  aggregate_metrics: AggregateMetrics;
  created_at: string;
  completed_at: string | null;
}

export interface Score {
  item_id: string;
  dimensions: Record<string, number>;
  overall: number;
  pass: boolean;
  judge_reasoning: string;
  raw_response: string;
}

export interface AggregateMetrics {
  mean_score: number;
  median_score: number;
  pass_rate: number;
  score_distribution: Record<string, number>;
  total_items: number;
  passed_items: number;
  failed_items: number;
}

export interface ResultComparison {
  evaluation_ids: string[];
  results: Result[];
  comparison_metrics: Record<string, number[]>;
}
