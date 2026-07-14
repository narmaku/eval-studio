import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { ArenaResultsCard } from './ArenaResultsCard';
import type { ArenaLeaderboardResponse } from '@/types';

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

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

describe('ArenaResultsCard', () => {
  it('renders with leaderboard tab active by default', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    // Tab buttons should be present
    expect(screen.getByText('Leaderboard')).toBeInTheDocument();
    expect(screen.getByText('Scores')).toBeInTheDocument();

    // Leaderboard table headers should be visible
    expect(screen.getByText('Rank')).toBeInTheDocument();
    expect(screen.getByText('Model')).toBeInTheDocument();
    expect(screen.getByText('Avg Score')).toBeInTheDocument();
    expect(screen.getByText('Passed')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Errored')).toBeInTheDocument();
  });

  it('renders all contestant rows in leaderboard tab', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('anthropic/claude-3')).toBeInTheDocument();
    expect(screen.getByText('local/llama-3')).toBeInTheDocument();
  });

  it('displays scores as percentages', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('displays rank badges with correct numbers', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    const rows = screen.getAllByRole('row');
    // Header + 3 data rows
    expect(rows).toHaveLength(4);

    // Check rank badges — they live inside Badge elements (data-slot="badge")
    const firstRowBadges = within(rows[1]!)
      .getAllByText(/^\d+$/)
      .filter((el) => el.getAttribute('data-slot') === 'badge');
    expect(firstRowBadges[0]).toHaveTextContent('1');

    const secondRowBadges = within(rows[2]!)
      .getAllByText(/^\d+$/)
      .filter((el) => el.getAttribute('data-slot') === 'badge');
    expect(secondRowBadges[0]).toHaveTextContent('2');

    const thirdRowBadges = within(rows[3]!)
      .getAllByText(/^\d+$/)
      .filter((el) => el.getAttribute('data-slot') === 'badge');
    expect(thirdRowBadges[0]).toHaveTextContent('3');
  });

  it('highlights first-place row with yellow background', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    const rows = screen.getAllByRole('row');
    expect(rows[1]!.className).toContain('bg-yellow');
    expect(rows[2]!.className).not.toContain('bg-yellow');
  });

  it('applies green color class for high scores (>= 70%)', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    const scoreCell = screen.getByText('85%');
    expect(scoreCell.className).toContain('green');
  });

  it('applies yellow color class for medium scores (>= 40%)', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    const scoreCell = screen.getByText('65%');
    expect(scoreCell.className).toContain('yellow');
  });

  it('applies red color class for low scores (< 40%)', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    const scoreCell = screen.getByText('30%');
    expect(scoreCell.className).toContain('red');
  });

  it('shows Error badge for fully errored contestants', () => {
    const errorLeaderboard: ArenaLeaderboardResponse = {
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
    render(<ArenaResultsCard leaderboard={errorLeaderboard} />);

    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('does not show Error badge for partially errored contestants', () => {
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
    render(<ArenaResultsCard leaderboard={partialError} />);

    expect(screen.queryByText('Error')).not.toBeInTheDocument();
    expect(screen.getByText('35%')).toBeInTheDocument();
  });

  it('shows empty state when no contestants', () => {
    const emptyLeaderboard: ArenaLeaderboardResponse = {
      evaluation_id: 'eval-1',
      evaluation_name: 'Empty Arena',
      contestants: [],
    };
    render(<ArenaResultsCard leaderboard={emptyLeaderboard} />);

    expect(screen.getByText(/no contestants to display/i)).toBeInTheDocument();
  });

  it('switches to scores tab when clicked', async () => {
    const user = userEvent.setup();
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    // Click Scores tab
    await user.click(screen.getByText('Scores'));

    // Table should no longer be visible (chart renders instead)
    expect(screen.queryByText('Rank')).not.toBeInTheDocument();
    expect(screen.queryByText('Passed')).not.toBeInTheDocument();
  });

  it('switches back to leaderboard tab', async () => {
    const user = userEvent.setup();
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    // Switch to Scores then back
    await user.click(screen.getByText('Scores'));
    await user.click(screen.getByText('Leaderboard'));

    // Table should be visible again
    expect(screen.getByText('Rank')).toBeInTheDocument();
    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
  });

  it('displays passed, failed, and errored counts', () => {
    render(<ArenaResultsCard leaderboard={mockLeaderboard} />);

    const rows = screen.getAllByRole('row');
    // First contestant: passed=8, failed=2, errored=0
    const firstRow = within(rows[1]!);
    expect(firstRow.getByText('8')).toBeInTheDocument();
    expect(firstRow.getByText('2')).toBeInTheDocument();
    expect(firstRow.getByText('0')).toBeInTheDocument();
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
    render(<ArenaResultsCard leaderboard={singleContestant} />);

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('82%')).toBeInTheDocument();
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(2); // header + 1 data row
  });

  it('applies custom className', () => {
    const { container } = render(
      <ArenaResultsCard leaderboard={mockLeaderboard} className="my-custom-class" />,
    );

    const card = container.firstElementChild;
    expect(card?.className).toContain('my-custom-class');
  });

  it('applies score boundary color at exactly 0.4', () => {
    const boundary: ArenaLeaderboardResponse = {
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
    render(<ArenaResultsCard leaderboard={boundary} />);

    const scoreCell = screen.getByText('40%');
    expect(scoreCell.className).toContain('yellow');
  });

  it('applies score boundary color at exactly 0.7', () => {
    const boundary: ArenaLeaderboardResponse = {
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
    render(<ArenaResultsCard leaderboard={boundary} />);

    const scoreCell = screen.getByText('70%');
    expect(scoreCell.className).toContain('green');
  });
});
