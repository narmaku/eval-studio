import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock all child components to isolate page logic
vi.mock('@/components/evaluation/EvaluatorSelector', () => ({
  EvaluatorSelector: ({ mode }: { mode: string }) => (
    <div data-testid="evaluator-selector">Evaluator Selector (mode={mode})</div>
  ),
}));

vi.mock('@/components/evaluation/ContestantSelector', () => ({
  ContestantSelector: ({
    value,
    onChange,
    disabled: _disabled,
  }: {
    value: unknown[];
    onChange: (v: unknown[]) => void;
    disabled?: boolean;
  }) => (
    <div data-testid="contestant-selector">
      Contestant Selector ({value.length} contestants)
      <button
        data-testid="mock-add-contestant"
        onClick={() => onChange([...value, { name: 'Model X', litellm_model: 'openai/gpt-4o' }])}
      >
        Mock Add
      </button>
    </div>
  ),
}));

vi.mock('@/components/evaluation/DatasetSelector', () => ({
  DatasetSelector: ({
    value: _value,
    onChange,
  }: {
    value: string | undefined;
    onChange: (v: string) => void;
  }) => (
    <div data-testid="dataset-selector">
      <button data-testid="mock-select-dataset" onClick={() => onChange('ds-1')}>
        Select Dataset
      </button>
    </div>
  ),
}));

vi.mock('@/components/evaluation/JudgeConfigPanel', () => ({
  JudgeConfigPanel: ({
    value: _value,
    onChange,
  }: {
    value: unknown;
    onChange: (v: unknown) => void;
  }) => (
    <div data-testid="judge-config">
      <button data-testid="mock-select-judge" onClick={() => onChange({ provider_id: 'judge-1' })}>
        Select Judge
      </button>
    </div>
  ),
}));

vi.mock('@/components/evaluation/EvaluationProgress', () => ({
  EvaluationProgress: ({
    evaluationId,
    onComplete,
  }: {
    evaluationId: string;
    onComplete: () => void;
  }) => (
    <div data-testid="evaluation-progress">
      Progress for {evaluationId}
      <button data-testid="mock-complete" onClick={onComplete}>
        Complete
      </button>
    </div>
  ),
}));

vi.mock('@/components/evaluation/ArenaLeaderboard', () => ({
  ArenaLeaderboard: () => <div data-testid="arena-leaderboard">Leaderboard</div>,
}));

vi.mock('@/components/evaluation/ArenaResultsGrid', () => ({
  ArenaResultsGrid: () => <div data-testid="arena-results-grid">Results Grid</div>,
}));

// Mock stores
const mockCreateAndRunEvaluation = vi.fn();
const mockSetCurrentEvaluation = vi.fn();
const mockFetchResults = vi.fn();
const mockResetSelection = vi.fn();
const mockGetArenaLeaderboard = vi.fn();

vi.mock('@/stores/evaluationStore', () => ({
  useEvaluationStore: Object.assign(
    vi.fn(() => ({
      currentEvaluation: null,
      createAndRunEvaluation: mockCreateAndRunEvaluation,
      setCurrentEvaluation: mockSetCurrentEvaluation,
      isLoading: false,
    })),
    {
      getState: () => ({
        currentEvaluation: { id: 'eval-123', status: 'completed', name: 'Arena Test' },
      }),
    },
  ),
}));

vi.mock('@/stores/evaluatorStore', () => ({
  useEvaluatorStore: Object.assign(
    vi.fn(() => ({
      selectedEvaluatorId: 'eval-1',
    })),
    {
      getState: () => ({
        resetSelection: mockResetSelection,
      }),
    },
  ),
}));

vi.mock('@/stores/resultStore', () => ({
  useResultStore: vi.fn(() => ({
    results: [],
    fetchResults: mockFetchResults,
  })),
}));

vi.mock('@/services/api', () => ({
  api: {
    getArenaLeaderboard: mockGetArenaLeaderboard,
  },
}));

vi.mock('@/stores/notificationStore', () => ({
  useNotificationStore: Object.assign(
    vi.fn(() => ({})),
    {
      getState: () => ({
        addNotification: vi.fn(),
      }),
    },
  ),
}));

describe('ArenaComparison page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderPage() {
    const mod = await import('./ArenaComparison');
    const ArenaComparison = mod.default;
    return render(<ArenaComparison />);
  }

  it('renders page heading', async () => {
    await renderPage();
    expect(screen.getByRole('heading', { name: /model arena/i })).toBeInTheDocument();
  });

  it('renders configure phase with all selectors', async () => {
    await renderPage();

    expect(screen.getByTestId('evaluator-selector')).toBeInTheDocument();
    expect(screen.getByTestId('contestant-selector')).toBeInTheDocument();
    expect(screen.getByTestId('dataset-selector')).toBeInTheDocument();
    expect(screen.getByTestId('judge-config')).toBeInTheDocument();
  });

  it('renders evaluator selector with mode="qa"', async () => {
    await renderPage();

    expect(screen.getByText(/mode=qa/)).toBeInTheDocument();
  });

  it('has Start Arena button', async () => {
    await renderPage();

    expect(screen.getByRole('button', { name: /start arena/i })).toBeInTheDocument();
  });

  it('Start Arena button is disabled when config is incomplete', async () => {
    await renderPage();

    const startButton = screen.getByRole('button', { name: /start arena/i });
    expect(startButton).toBeDisabled();
  });

  it('enables Start Arena button when all config is provided', async () => {
    const user = userEvent.setup();
    await renderPage();

    // Need: >=2 contestants + dataset + judge + evaluator (already mocked)
    // Add 2 contestants
    await user.click(screen.getByTestId('mock-add-contestant'));
    await user.click(screen.getByTestId('mock-add-contestant'));
    // Select dataset
    await user.click(screen.getByTestId('mock-select-dataset'));
    // Select judge
    await user.click(screen.getByTestId('mock-select-judge'));

    const startButton = screen.getByRole('button', { name: /start arena/i });
    expect(startButton).not.toBeDisabled();
  });

  it('transitions to running phase when start is clicked', async () => {
    const user = userEvent.setup();
    mockCreateAndRunEvaluation.mockResolvedValue({ id: 'eval-123', status: 'running' });

    // Need to re-mock useEvaluationStore to return a currentEvaluation after creation
    const { useEvaluationStore } = await import('@/stores/evaluationStore');
    (useEvaluationStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      currentEvaluation: { id: 'eval-123', status: 'running' },
      createAndRunEvaluation: mockCreateAndRunEvaluation,
      setCurrentEvaluation: mockSetCurrentEvaluation,
      isLoading: false,
    });

    await renderPage();

    // Setup config
    await user.click(screen.getByTestId('mock-add-contestant'));
    await user.click(screen.getByTestId('mock-add-contestant'));
    await user.click(screen.getByTestId('mock-select-dataset'));
    await user.click(screen.getByTestId('mock-select-judge'));

    await user.click(screen.getByRole('button', { name: /start arena/i }));

    await waitFor(() => {
      expect(screen.getByTestId('evaluation-progress')).toBeInTheDocument();
    });
  });

  it('shows New Arena button in complete phase', async () => {
    const { useEvaluationStore } = await import('@/stores/evaluationStore');
    (useEvaluationStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      currentEvaluation: { id: 'eval-123', status: 'completed', name: 'Arena Test' },
      createAndRunEvaluation: mockCreateAndRunEvaluation,
      setCurrentEvaluation: mockSetCurrentEvaluation,
      isLoading: false,
    });

    mockGetArenaLeaderboard.mockResolvedValue({
      evaluation_id: 'eval-123',
      evaluation_name: 'Arena Test',
      contestants: [],
    });

    const user = userEvent.setup();

    await renderPage();

    // Setup config and start
    await user.click(screen.getByTestId('mock-add-contestant'));
    await user.click(screen.getByTestId('mock-add-contestant'));
    await user.click(screen.getByTestId('mock-select-dataset'));
    await user.click(screen.getByTestId('mock-select-judge'));
    await user.click(screen.getByRole('button', { name: /start arena/i }));

    // Wait for running phase
    await waitFor(() => {
      expect(screen.getByTestId('evaluation-progress')).toBeInTheDocument();
    });

    // Simulate completion
    await user.click(screen.getByTestId('mock-complete'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new arena/i })).toBeInTheDocument();
    });
  });
});
