import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import type { Session } from '@/types';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the API to return sessions directly
vi.mock('@/services/api', () => ({
  api: {
    listSessions: vi.fn(),
  },
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

function makeSession(overrides: Partial<Session> = {}): Session {
  return {
    id: 'sess-1',
    evaluation_id: 'eval-1',
    mode: 'live',
    status: 'active',
    agent_config: null,
    judge_config_snapshot: null,
    transcript: [],
    name: 'Test Session',
    scores: null,
    error: null,
    started_at: '2026-01-01T00:00:00Z',
    ended_at: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('Sessions page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderPage(sessions: Session[] = []) {
    mockedApi.listSessions.mockResolvedValue({
      items: sessions,
      total: sessions.length,
      page: 1,
      page_size: 50,
      pages: 1,
    });

    const mod = await import('./Sessions');
    const Sessions = mod.default;
    const result = render(
      <MemoryRouter>
        <Sessions />
      </MemoryRouter>,
    );

    // Wait for loading to complete
    if (sessions.length > 0) {
      await waitFor(() => {
        expect(screen.queryByText('Loading sessions...')).not.toBeInTheDocument();
      });
    }

    return result;
  }

  it('renders page heading', async () => {
    await renderPage();
    expect(screen.getByRole('heading', { name: /sessions/i })).toBeInTheDocument();
  });

  it('shows empty state when no sessions', async () => {
    await renderPage([]);
    await waitFor(() => {
      expect(screen.getByText(/no sessions yet/i)).toBeInTheDocument();
    });
  });

  describe('status badges', () => {
    it('shows Active badge for active sessions', async () => {
      await renderPage([makeSession({ status: 'active' })]);
      expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('shows Ended badge for ended sessions', async () => {
      await renderPage([makeSession({ status: 'ended', ended_at: '2026-01-01T00:05:00Z' })]);
      expect(screen.getByText('Ended')).toBeInTheDocument();
    });

    it('shows Scoring... badge for scoring sessions', async () => {
      await renderPage([makeSession({ status: 'scoring', ended_at: '2026-01-01T00:05:00Z' })]);
      expect(screen.getByText('Scoring...')).toBeInTheDocument();
    });

    it('shows Scored badge for completed sessions', async () => {
      await renderPage([
        makeSession({
          status: 'completed',
          ended_at: '2026-01-01T00:05:00Z',
          scores: { overall: 0.85, passed: true, reasoning: null, breakdown: null },
        }),
      ]);
      expect(screen.getByText('Scored')).toBeInTheDocument();
    });

  });

  describe('score column', () => {
    it('shows Score button for ended sessions', async () => {
      await renderPage([
        makeSession({ id: 'sess-ended', status: 'ended', ended_at: '2026-01-01T00:05:00Z' }),
      ]);
      expect(screen.getByRole('button', { name: /score/i })).toBeInTheDocument();
    });

    it('Score button navigates to session detail', async () => {
      const user = userEvent.setup();
      await renderPage([
        makeSession({ id: 'sess-ended', status: 'ended', ended_at: '2026-01-01T00:05:00Z' }),
      ]);

      await user.click(screen.getByRole('button', { name: /score/i }));
      expect(mockNavigate).toHaveBeenCalledWith('/sessions/sess-ended');
    });

    it('shows percentage for completed sessions with scores', async () => {
      await renderPage([
        makeSession({
          status: 'completed',
          ended_at: '2026-01-01T00:05:00Z',
          scores: { overall: 0.85, passed: true, reasoning: null, breakdown: null },
        }),
      ]);
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('shows -- for active sessions without scores', async () => {
      await renderPage([makeSession({ status: 'active' })]);
      // The Score column for active sessions should show '--'
      const cells = screen.getAllByRole('cell');
      // Find the score cell (6th column, index 5 in each row)
      const scoreCells = cells.filter((cell) => cell.textContent === '--');
      expect(scoreCells.length).toBeGreaterThanOrEqual(1);
    });
  });
});
