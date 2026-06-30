import type { components } from './generated/api';

export type ScoreBucket = components['schemas']['ScoreBucket'];

export interface RetrievedChunk {
  content: string;
  source?: string;
  relevance_score?: number;
}

export interface Result {
  id: string;
  evaluation_id: string;
  dataset_item_id: string | null;
  session_id: string | null;
  contestant_model: string | null;
  name?: string | null;
  score: number | null;
  passed: boolean | null;
  actual_answer: string | null;
  judge_reasoning: string | null;
  scores_breakdown: Record<string, number> | null;
  retrieved_chunks: RetrievedChunk[] | null;
  tags?: string[];
  created_at: string;
  updated_at?: string;
}

export interface UpdateResultRequest {
  name?: string;
  tags?: string[];
}

export interface ArenaContestantSummary {
  contestant_model: string;
  total_items: number;
  passed_count: number;
  failed_count: number;
  errored_count: number;
  average_score: number;
  min_score: number | null;
  max_score: number | null;
  average_breakdown: Record<string, number> | null;
}

export interface ArenaLeaderboardResponse {
  evaluation_id: string;
  evaluation_name: string;
  contestants: ArenaContestantSummary[];
}

export interface AggregateMetrics {
  mean_score: number;
  median_score: number;
  pass_rate: number;
  score_distribution: ScoreBucket[];
  total_items: number;
  passed_items: number;
  failed_items: number;
}

export interface EvaluationComparisonItem {
  evaluation_id: string;
  evaluation_name: string;
  total_items: number;
  passed_count: number;
  failed_count: number;
  average_score: number;
  min_score: number | null;
  max_score: number | null;
  results: Result[];
}

export interface CrossEvaluationItemComparison {
  dataset_item_id: string;
  results: Result[];
}

export interface ComparisonResponse {
  evaluations: EvaluationComparisonItem[];
  item_comparisons: CrossEvaluationItemComparison[];
  reference_evaluation_id: string | null;
}
