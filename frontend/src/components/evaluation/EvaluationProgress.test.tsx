import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvaluationProgress } from './EvaluationProgress';

const mockConnectToEvaluation = vi.fn();
const mockDisconnectFromEvaluation = vi.fn();

let mockCurrentEvaluation: { status: string } | null = null;
let mockProgress: {
  completed: number;
  total: number;
  currentItem: string;
  contestantModel?: string;
} | null = null;
let mockLogs: unknown[] = [];

const getState = () => ({
  currentEvaluation: mockCurrentEvaluation,
  progress: mockProgress,
  connectToEvaluation: mockConnectToEvaluation,
  disconnectFromEvaluation: mockDisconnectFromEvaluation,
  logs: mockLogs,
});

vi.mock('@/stores/evaluationStore', () => ({
  useEvaluationStore: vi.fn((selector?: (state: ReturnType<typeof getState>) => unknown) => {
    const state = getState();
    if (typeof selector === 'function') {
      return selector(state);
    }
    return state;
  }),
}));

describe('EvaluationProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCurrentEvaluation = { status: 'running' };
    mockProgress = null;
    mockLogs = [];
  });

  it('renders with running status', () => {
    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Evaluation Progress')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('connects to WebSocket on mount', () => {
    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(mockConnectToEvaluation).toHaveBeenCalledWith('eval-123');
  });

  it('disconnects from WebSocket on unmount', () => {
    const { unmount } = render(
      <EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />,
    );

    unmount();

    expect(mockDisconnectFromEvaluation).toHaveBeenCalled();
  });

  it('shows determinate progress bar with completed/total', () => {
    mockProgress = { completed: 5, total: 10, currentItem: 'What is RHEL?' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('5 / 10')).toBeInTheDocument();
  });

  it('shows current item text', () => {
    mockProgress = { completed: 3, total: 10, currentItem: 'What is Fedora?' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText(/What is Fedora/)).toBeInTheDocument();
  });

  it('shows contestant model for arena mode', () => {
    mockProgress = {
      completed: 3,
      total: 8,
      currentItem: 'What is Fedora?',
      contestantModel: 'gpt-4',
    };

    render(<EvaluationProgress evaluationId="eval-arena" onComplete={vi.fn()} />);

    expect(screen.getByText(/gpt-4/)).toBeInTheDocument();
  });

  it('shows completed status when evaluation is completed', () => {
    mockCurrentEvaluation = { status: 'completed' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('shows failed status when evaluation failed', () => {
    mockCurrentEvaluation = { status: 'failed' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('shows indeterminate progress when no progress data', () => {
    mockProgress = null;

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    // Should show "Scoring items..." text (indeterminate state)
    expect(screen.getByText('Scoring items...')).toBeInTheDocument();
  });
});
