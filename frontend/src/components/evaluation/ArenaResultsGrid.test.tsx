import { render, screen, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ArenaResultsGrid } from './ArenaResultsGrid';
import type { Result } from '@/types';

function makeResult(overrides: Partial<Result> & { dataset_item_id: string; contestant_model: string }): Result {
  return {
    id: `result-${overrides.dataset_item_id}-${overrides.contestant_model}`,
    evaluation_id: 'eval-1',
    dataset_item_id: overrides.dataset_item_id,
    session_id: null,
    contestant_model: overrides.contestant_model,
    score: overrides.score ?? 0.8,
    passed: overrides.passed ?? true,
    actual_answer: overrides.actual_answer ?? 'Some answer',
    judge_reasoning: overrides.judge_reasoning ?? null,
    scores_breakdown: null,
    retrieved_chunks: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

const twoContestants = ['openai/gpt-4o', 'anthropic/claude-3'];

const twoContestantResults: Result[] = [
  makeResult({ dataset_item_id: 'q1', contestant_model: 'openai/gpt-4o', actual_answer: 'GPT answer 1', score: 0.9, passed: true }),
  makeResult({ dataset_item_id: 'q1', contestant_model: 'anthropic/claude-3', actual_answer: 'Claude answer 1', score: 0.7, passed: true }),
  makeResult({ dataset_item_id: 'q2', contestant_model: 'openai/gpt-4o', actual_answer: 'GPT answer 2', score: 0.6, passed: false }),
  makeResult({ dataset_item_id: 'q2', contestant_model: 'anthropic/claude-3', actual_answer: 'Claude answer 2', score: 0.4, passed: false }),
];

describe('ArenaResultsGrid', () => {
  it('renders column headers for each contestant', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('anthropic/claude-3')).toBeInTheDocument();
  });

  it('renders a row for each unique dataset item', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    // Two questions, so 2 data rows + 1 header row
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3); // header + 2 data rows
  });

  it('shows actual answers for each contestant in each row', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    expect(screen.getByText(/GPT answer 1/)).toBeInTheDocument();
    expect(screen.getByText(/Claude answer 1/)).toBeInTheDocument();
    expect(screen.getByText(/GPT answer 2/)).toBeInTheDocument();
    expect(screen.getByText(/Claude answer 2/)).toBeInTheDocument();
  });

  it('shows score badges for each result', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('70%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
  });

  it('handles missing results for a contestant gracefully', () => {
    const partialResults: Result[] = [
      makeResult({ dataset_item_id: 'q1', contestant_model: 'openai/gpt-4o', actual_answer: 'GPT only' }),
      // No result for claude on q1
    ];

    render(<ArenaResultsGrid results={partialResults} contestants={twoContestants} />);

    expect(screen.getByText(/GPT only/)).toBeInTheDocument();
    // Should show a placeholder for the missing result
    expect(screen.getByText('--')).toBeInTheDocument();
  });

  it('renders empty state when no results', () => {
    render(<ArenaResultsGrid results={[]} contestants={twoContestants} />);

    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });

  it('renders side-by-side for 2-3 contestants', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    // The table should be rendered (side-by-side layout for 2 contestants)
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  });

  it('renders with horizontal scroll for 4+ contestants', () => {
    const fiveContestants = ['model-1', 'model-2', 'model-3', 'model-4', 'model-5'];
    const results: Result[] = fiveContestants.map((model) =>
      makeResult({ dataset_item_id: 'q1', contestant_model: model, actual_answer: `${model} answer` }),
    );

    render(<ArenaResultsGrid results={results} contestants={fiveContestants} />);

    // All 5 models should still be visible as column headers
    fiveContestants.forEach((model) => {
      expect(screen.getByText(model)).toBeInTheDocument();
    });
  });

  it('truncates long answers', () => {
    const longAnswer = 'A'.repeat(200);
    const results: Result[] = [
      makeResult({ dataset_item_id: 'q1', contestant_model: 'openai/gpt-4o', actual_answer: longAnswer }),
    ];

    render(<ArenaResultsGrid results={results} contestants={['openai/gpt-4o']} />);

    // Should show truncated text
    const truncated = screen.getByText(/A{1,}\.\.\.$/);
    expect(truncated).toBeInTheDocument();
  });
});
