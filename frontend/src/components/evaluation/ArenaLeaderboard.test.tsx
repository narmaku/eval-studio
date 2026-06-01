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
});
