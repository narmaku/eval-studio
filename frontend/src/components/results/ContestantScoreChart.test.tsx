import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ContestantScoreChart } from './ContestantScoreChart';
import type { ArenaContestantSummary } from '@/types';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

const makeContestant = (
  model: string,
  score: number,
  breakdown?: Record<string, number> | null,
): ArenaContestantSummary => ({
  contestant_model: model,
  total_items: 10,
  passed_count: Math.round(score * 10),
  failed_count: 10 - Math.round(score * 10),
  errored_count: 0,
  average_score: score,
  min_score: score - 0.1,
  max_score: score + 0.1,
  average_breakdown: breakdown ?? null,
});

describe('ContestantScoreChart', () => {
  it('renders with contestants', () => {
    const contestants = [
      makeContestant('openai/gpt-4o', 0.85),
      makeContestant('anthropic/claude-3', 0.72),
    ];

    render(<ContestantScoreChart contestants={contestants} />);

    expect(screen.getByText('Contestant Score Comparison')).toBeInTheDocument();
  });

  it('returns null when no contestants provided', () => {
    const { container } = render(<ContestantScoreChart contestants={[]} />);

    expect(container.innerHTML).toBe('');
  });

  it('renders a single contestant', () => {
    const contestants = [makeContestant('model-a', 0.9)];

    render(<ContestantScoreChart contestants={contestants} />);

    expect(screen.getByText('Contestant Score Comparison')).toBeInTheDocument();
  });

  it('renders multiple contestants', () => {
    const contestants = [
      makeContestant('model-a', 0.9),
      makeContestant('model-b', 0.7),
      makeContestant('model-c', 0.5),
    ];

    render(<ContestantScoreChart contestants={contestants} />);

    expect(screen.getByText('Contestant Score Comparison')).toBeInTheDocument();
  });
});
