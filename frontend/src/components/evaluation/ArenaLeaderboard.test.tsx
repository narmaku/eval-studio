import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ArenaLeaderboard } from './ArenaLeaderboard';
import type { ArenaLeaderboardResponse } from '@/types';

const mockLeaderboard: ArenaLeaderboardResponse = {
  evaluation_id: 'eval-1',
  evaluation_name: 'Arena Test',
  contestants: [
    {
      contestant_model: 'openai/gpt-4o',
      total_items: 10,
      passed_count: 8,
      failed_count: 2,
      errored_count: 0,
      average_score: 0.85,
      min_score: 0.5,
      max_score: 1.0,
      average_breakdown: null,
    },
    {
      contestant_model: 'anthropic/claude-3',
      total_items: 10,
      passed_count: 6,
      failed_count: 3,
      errored_count: 1,
      average_score: 0.65,
      min_score: 0.2,
      max_score: 0.9,
      average_breakdown: null,
    },
    {
      contestant_model: 'local/llama-3',
      total_items: 10,
      passed_count: 2,
      failed_count: 5,
      errored_count: 3,
      average_score: 0.3,
      min_score: 0.0,
      max_score: 0.6,
      average_breakdown: null,
    },
  ],
};

describe('ArenaLeaderboard', () => {
  it('renders a table with correct headers', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    expect(screen.getByText('Rank')).toBeInTheDocument();
    expect(screen.getByText('Model')).toBeInTheDocument();
    expect(screen.getByText('Avg Score')).toBeInTheDocument();
    expect(screen.getByText('Passed')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Errored')).toBeInTheDocument();
  });

  it('renders all contestant rows', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('anthropic/claude-3')).toBeInTheDocument();
    expect(screen.getByText('local/llama-3')).toBeInTheDocument();
  });

  it('displays ranked numbers starting from 1', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    // Rank badges
    const cells = screen.getAllByRole('cell');
    // First row should have rank 1
    expect(cells[0]).toHaveTextContent('1');
  });

  it('formats scores as percentages', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('displays passed, failed, and errored counts', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    // Check that the numbers are present in the correct rows
    const rows = screen.getAllByRole('row');
    // Header row + 3 data rows
    expect(rows).toHaveLength(4);
  });

  it('handles empty leaderboard gracefully', () => {
    const emptyLeaderboard: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Empty Arena',
      contestants: [],
    };
    render(<ArenaLeaderboard leaderboard={emptyLeaderboard} />);

    expect(screen.getByText(/no contestants/i)).toBeInTheDocument();
  });

  it('shows "Error" indicator for contestants where all items errored', () => {
    const leaderboardWithError: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Error Arena',
      contestants: [
        {
          contestant_model: 'broken-model',
          total_items: 10,
          passed_count: 0,
          failed_count: 0,
          errored_count: 10,
          average_score: 0,
          min_score: null,
          max_score: null,
          average_breakdown: null,
        },
      ],
    };
    render(<ArenaLeaderboard leaderboard={leaderboardWithError} />);

    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('applies green color class for high scores (>= 70%)', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    const scoreCell = screen.getByText('85%');
    expect(scoreCell.className).toContain('green');
  });

  it('applies yellow color class for medium scores (>= 40%)', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    const scoreCell = screen.getByText('65%');
    expect(scoreCell.className).toContain('yellow');
  });

  it('applies red color class for low scores (< 40%)', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    const scoreCell = screen.getByText('30%');
    expect(scoreCell.className).toContain('red');
  });

  it('renders a single contestant correctly', () => {
    const singleContestant: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Single Arena',
      contestants: [
        {
          contestant_model: 'openai/gpt-4o',
          total_items: 5,
          passed_count: 4,
          failed_count: 1,
          errored_count: 0,
          average_score: 0.82,
          min_score: 0.5,
          max_score: 1.0,
          average_breakdown: null,
        },
      ],
    };
    render(<ArenaLeaderboard leaderboard={singleContestant} />);

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('82%')).toBeInTheDocument();
    // Only header + 1 data row
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(2);
  });

  it('handles tie scores by listing in given order', () => {
    const tieLeaderboard: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Tie Arena',
      contestants: [
        {
          contestant_model: 'model-a',
          total_items: 10,
          passed_count: 7,
          failed_count: 3,
          errored_count: 0,
          average_score: 0.7,
          min_score: 0.3,
          max_score: 1.0,
          average_breakdown: null,
        },
        {
          contestant_model: 'model-b',
          total_items: 10,
          passed_count: 7,
          failed_count: 3,
          errored_count: 0,
          average_score: 0.7,
          min_score: 0.3,
          max_score: 1.0,
          average_breakdown: null,
        },
      ],
    };
    render(<ArenaLeaderboard leaderboard={tieLeaderboard} />);

    expect(screen.getByText('model-a')).toBeInTheDocument();
    expect(screen.getByText('model-b')).toBeInTheDocument();
    // Both should show 70%
    const scores = screen.getAllByText('70%');
    expect(scores).toHaveLength(2);
  });

  it('highlights first row with special background class', () => {
    render(<ArenaLeaderboard leaderboard={mockLeaderboard} />);

    const rows = screen.getAllByRole('row');
    // First data row (index 1, since index 0 is header)
    expect(rows[1]!.className).toContain('bg-yellow');
    // Second data row should NOT have the highlight
    expect(rows[2]!.className).not.toContain('bg-yellow');
  });

  it('renders all contestants as errored when all have 100% errors', () => {
    const allErrored: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'All Errored',
      contestants: [
        {
          contestant_model: 'broken-1',
          total_items: 5,
          passed_count: 0,
          failed_count: 0,
          errored_count: 5,
          average_score: 0,
          min_score: null,
          max_score: null,
          average_breakdown: null,
        },
        {
          contestant_model: 'broken-2',
          total_items: 5,
          passed_count: 0,
          failed_count: 0,
          errored_count: 5,
          average_score: 0,
          min_score: null,
          max_score: null,
          average_breakdown: null,
        },
      ],
    };
    render(<ArenaLeaderboard leaderboard={allErrored} />);

    const errorBadges = screen.getAllByText('Error');
    expect(errorBadges).toHaveLength(2);
  });

  it('applies yellow for a score at exactly 0.4 boundary', () => {
    const boundaryLeaderboard: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Boundary',
      contestants: [
        {
          contestant_model: 'boundary-model',
          total_items: 10,
          passed_count: 4,
          failed_count: 6,
          errored_count: 0,
          average_score: 0.4,
          min_score: 0.1,
          max_score: 0.8,
          average_breakdown: null,
        },
      ],
    };
    render(<ArenaLeaderboard leaderboard={boundaryLeaderboard} />);

    const scoreCell = screen.getByText('40%');
    expect(scoreCell.className).toContain('yellow');
  });

  it('applies green for a score at exactly 0.7 boundary', () => {
    const boundaryLeaderboard: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Boundary',
      contestants: [
        {
          contestant_model: 'boundary-model',
          total_items: 10,
          passed_count: 7,
          failed_count: 3,
          errored_count: 0,
          average_score: 0.7,
          min_score: 0.2,
          max_score: 1.0,
          average_breakdown: null,
        },
      ],
    };
    render(<ArenaLeaderboard leaderboard={boundaryLeaderboard} />);

    const scoreCell = screen.getByText('70%');
    expect(scoreCell.className).toContain('green');
  });

  it('does not show Error badge for partially errored contestant', () => {
    const partialError: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Partial Error',
      contestants: [
        {
          contestant_model: 'partial-model',
          total_items: 10,
          passed_count: 3,
          failed_count: 2,
          errored_count: 5,
          average_score: 0.35,
          min_score: 0.0,
          max_score: 0.8,
          average_breakdown: null,
        },
      ],
    };
    render(<ArenaLeaderboard leaderboard={partialError} />);

    // Should show a score percentage, not "Error"
    expect(screen.queryByText('Error')).not.toBeInTheDocument();
    expect(screen.getByText('35%')).toBeInTheDocument();
  });
});
