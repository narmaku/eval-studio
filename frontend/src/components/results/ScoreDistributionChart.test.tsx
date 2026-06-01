import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ScoreDistributionChart } from './ScoreDistributionChart';
import { bucketScores } from './scoreUtils';
import type { Result } from '@/types';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

let idCounter = 0;
const makeResult = (score: number): Result => ({
  id: `r-${++idCounter}`,
  evaluation_id: 'e1',
  dataset_item_id: `item-${score}`,
  session_id: null,
  contestant_model: null,
  score,
  passed: score >= 0.5,
  actual_answer: 'test',
  judge_reasoning: 'test',
  scores_breakdown: null,
  retrieved_chunks: null,
  created_at: '2026-01-01T00:00:00Z',
});

describe('bucketScores', () => {
  it('buckets scores into 10 bins', () => {
    const scores = [
      makeResult(0.05),
      makeResult(0.15),
      makeResult(0.25),
      makeResult(0.85),
      makeResult(0.95),
      makeResult(1.0),
    ];

    const buckets = bucketScores(scores);

    expect(buckets).toHaveLength(10);
    expect(buckets[0]!.count).toBe(1); // 0.0-0.1
    expect(buckets[1]!.count).toBe(1); // 0.1-0.2
    expect(buckets[2]!.count).toBe(1); // 0.2-0.3
    expect(buckets[8]!.count).toBe(1); // 0.8-0.9
    expect(buckets[9]!.count).toBe(2); // 0.9-1.0 (includes 0.95 and 1.0)
  });

  it('handles empty scores', () => {
    const buckets = bucketScores([]);
    expect(buckets).toHaveLength(10);
    buckets.forEach((b) => expect(b.count).toBe(0));
  });

  it('places score of exactly 1.0 in the last bucket', () => {
    const scores = [makeResult(1.0)];
    const buckets = bucketScores(scores);
    expect(buckets[9]!.count).toBe(1);
  });

  it('places score of exactly 0.0 in the first bucket', () => {
    const scores = [makeResult(0.0)];
    const buckets = bucketScores(scores);
    expect(buckets[0]!.count).toBe(1);
  });
});

describe('ScoreDistributionChart', () => {
  it('renders with data without crashing', () => {
    const results = [makeResult(0.5), makeResult(0.7), makeResult(0.9)];
    const { container } = render(<ScoreDistributionChart results={results} />);

    expect(screen.getByText('Score Distribution')).toBeInTheDocument();
    // Recharts renders SVG in real DOM, but in jsdom it may not fully render.
    // Check the container exists.
    expect(container.querySelector('[data-slot="card"]')).toBeInTheDocument();
  });

  it('renders empty state when no scores provided', () => {
    render(<ScoreDistributionChart results={[]} />);
    expect(screen.getByText('No score data available.')).toBeInTheDocument();
  });
});
