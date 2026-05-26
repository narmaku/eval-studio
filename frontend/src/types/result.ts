// Types aligned with backend ResultResponse schema

export interface Result {
  id: string;
  evaluation_id: string;
  dataset_item_id: string | null;
  session_id: string | null;
  score: number | null;
  passed: boolean | null;
  actual_answer: string | null;
  judge_reasoning: string | null;
  scores_breakdown: Record<string, number> | null;
  created_at: string;
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
