import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ArenaResultsGrid } from './ArenaResultsGrid';
import type { Result } from '@/types';

vi.mock('@/services/api', () => ({
  api: {
    getDataset: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

function makeResult(
  overrides: Partial<Result> & { dataset_item_id: string; contestant_model: string },
): Result {
  const { dataset_item_id, contestant_model, ...rest } = overrides;
  return {
    id: `result-${dataset_item_id}-${contestant_model}`,
    evaluation_id: 'eval-1',
    dataset_item_id,
    session_id: null,
    contestant_model,
    score: 0.8,
    passed: true,
    actual_answer: 'Some answer',
    judge_reasoning: null,
    scores_breakdown: null,
    retrieved_chunks: null,
    created_at: '2026-01-01T00:00:00Z',
    ...rest,
  };
}

const twoContestants = ['openai/gpt-4o', 'anthropic/claude-3'];

const twoContestantResults: Result[] = [
  makeResult({
    dataset_item_id: 'q1',
    contestant_model: 'openai/gpt-4o',
    actual_answer: 'GPT answer 1',
    score: 0.9,
    passed: true,
  }),
  makeResult({
    dataset_item_id: 'q1',
    contestant_model: 'anthropic/claude-3',
    actual_answer: 'Claude answer 1',
    score: 0.7,
    passed: true,
  }),
  makeResult({
    dataset_item_id: 'q2',
    contestant_model: 'openai/gpt-4o',
    actual_answer: 'GPT answer 2',
    score: 0.6,
    passed: false,
  }),
  makeResult({
    dataset_item_id: 'q2',
    contestant_model: 'anthropic/claude-3',
    actual_answer: 'Claude answer 2',
    score: 0.4,
    passed: false,
  }),
];

describe('ArenaResultsGrid', () => {
  it('renders column headers for each contestant', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('anthropic/claude-3')).toBeInTheDocument();
  });

  it('renders a row for each unique dataset item', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3); // header + 2 data rows
  });

  it('shows score badges for each result', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('70%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
  });

  it('shows answers in expanded row when clicked', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    // Answers not visible initially
    expect(screen.queryByText('GPT answer 1')).not.toBeInTheDocument();

    // Click to expand first row
    const rows = screen.getAllByRole('row');
    fireEvent.click(rows[1]); // first data row

    // Now answers are visible
    expect(screen.getByText('GPT answer 1')).toBeInTheDocument();
    expect(screen.getByText('Claude answer 1')).toBeInTheDocument();
  });

  it('handles missing results for a contestant gracefully', () => {
    const partialResults: Result[] = [
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'openai/gpt-4o',
        actual_answer: 'GPT only',
      }),
    ];

    render(<ArenaResultsGrid results={partialResults} contestants={twoContestants} />);

    expect(screen.getByText('--')).toBeInTheDocument();
  });

  it('renders empty state when no results', () => {
    render(<ArenaResultsGrid results={[]} contestants={twoContestants} />);

    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });

  it('renders the table with expandable rows', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  });

  it('renders with horizontal scroll for 4+ contestants', () => {
    const fiveContestants = ['model-1', 'model-2', 'model-3', 'model-4', 'model-5'];
    const results: Result[] = fiveContestants.map((model) =>
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: model,
        actual_answer: `${model} answer`,
      }),
    );

    render(<ArenaResultsGrid results={results} contestants={fiveContestants} />);

    fiveContestants.forEach((model) => {
      expect(screen.getByText(model)).toBeInTheDocument();
    });
  });

  it('renders 0% for null score', () => {
    const results: Result[] = [
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'openai/gpt-4o',
        score: null,
        passed: null,
      }),
    ];

    render(<ArenaResultsGrid results={results} contestants={['openai/gpt-4o']} />);

    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('renders Pass badge for passing results', () => {
    const results: Result[] = [
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'openai/gpt-4o',
        score: 0.9,
        passed: true,
      }),
    ];

    render(<ArenaResultsGrid results={results} contestants={['openai/gpt-4o']} />);

    expect(screen.getByText('Pass')).toBeInTheDocument();
  });

  it('renders Fail badge for failing results', () => {
    const results: Result[] = [
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'openai/gpt-4o',
        score: 0.2,
        passed: false,
      }),
    ];

    render(<ArenaResultsGrid results={results} contestants={['openai/gpt-4o']} />);

    expect(screen.getByText('Fail')).toBeInTheDocument();
  });

  it('does not render Pass or Fail badge when passed is null', () => {
    const results: Result[] = [
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'openai/gpt-4o',
        score: 0.5,
        passed: null,
      }),
    ];

    render(<ArenaResultsGrid results={results} contestants={['openai/gpt-4o']} />);

    expect(screen.queryByText('Pass')).not.toBeInTheDocument();
    expect(screen.queryByText('Fail')).not.toBeInTheDocument();
  });

  it('renders Question column header', () => {
    render(<ArenaResultsGrid results={twoContestantResults} contestants={twoContestants} />);

    expect(screen.getByText('Question')).toBeInTheDocument();
  });

  it('applies score color classes correctly', () => {
    const results: Result[] = [
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'openai/gpt-4o',
        score: 0.85,
      }),
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'anthropic/claude-3',
        score: 0.5,
      }),
    ];

    render(<ArenaResultsGrid results={results} contestants={twoContestants} />);

    const highScore = screen.getByText('85%');
    expect(highScore.className).toContain('green');

    const midScore = screen.getByText('50%');
    expect(midScore.className).toContain('yellow');
  });

  it('shows "--" placeholder for all missing contestants in a row', () => {
    const results: Result[] = [
      makeResult({
        dataset_item_id: 'q1',
        contestant_model: 'unknown-model',
        actual_answer: 'some answer',
      }),
    ];

    render(<ArenaResultsGrid results={results} contestants={twoContestants} />);

    const dashes = screen.getAllByText('--');
    expect(dashes).toHaveLength(2);
  });
});
