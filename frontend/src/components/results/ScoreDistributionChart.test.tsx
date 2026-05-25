import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ScoreDistributionChart } from './ScoreDistributionChart';
import { bucketScores } from './scoreUtils';
import type { Score } from '@/types';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

const makeScore = (overall: number): Score => ({
  item_id: `item-${overall}`,
  dimensions: {},
  overall,
  pass: overall >= 0.5,
  judge_reasoning: 'test',
  raw_response: 'test',
});

describe('bucketScores', () => {
  it('buckets scores into 10 bins', () => {
    const scores = [
      makeScore(0.05),
      makeScore(0.15),
      makeScore(0.25),
      makeScore(0.85),
      makeScore(0.95),
      makeScore(1.0),
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
    const scores = [makeScore(1.0)];
    const buckets = bucketScores(scores);
    expect(buckets[9]!.count).toBe(1);
  });

  it('places score of exactly 0.0 in the first bucket', () => {
    const scores = [makeScore(0.0)];
    const buckets = bucketScores(scores);
    expect(buckets[0]!.count).toBe(1);
  });
});

describe('ScoreDistributionChart', () => {
  it('renders with data without crashing', () => {
    const scores = [makeScore(0.5), makeScore(0.7), makeScore(0.9)];
    const { container } = render(<ScoreDistributionChart scores={scores} />);

    expect(screen.getByText('Score Distribution')).toBeInTheDocument();
    // Recharts renders SVG in real DOM, but in jsdom it may not fully render.
    // Check the container exists.
    expect(container.querySelector('[data-slot="card"]')).toBeInTheDocument();
  });

  it('renders empty state when no scores provided', () => {
    render(<ScoreDistributionChart scores={[]} />);
    expect(screen.getByText('No score data available.')).toBeInTheDocument();
  });
});
