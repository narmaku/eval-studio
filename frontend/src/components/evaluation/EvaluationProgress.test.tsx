import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvaluationProgress } from './EvaluationProgress';

const mockConnectToEvaluation = vi.fn();

let mockCurrentEvaluation: { name?: string; status: string } | null = null;
let mockProgress: {
  completed: number;
  total: number;
  currentItem: string;
  contestantModel?: string;
} | null = null;
let mockLogs: unknown[] = [];

let mockWsConnection: { readyState: number } | null = null;
let mockConnectedEvaluationId: string | null = null;

const getState = () => ({
  currentEvaluation: mockCurrentEvaluation,
  progress: mockProgress,
  connectToEvaluation: mockConnectToEvaluation,
  logs: mockLogs,
  wsConnection: mockWsConnection,
  _connectedEvaluationId: mockConnectedEvaluationId,
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
    mockCurrentEvaluation = { name: 'Test Eval', status: 'running' };
    mockProgress = null;
    mockLogs = [];
    mockWsConnection = null;
    mockConnectedEvaluationId = null;
  });

  it('renders with running status', () => {
    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Test Eval')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('connects to WebSocket on mount', () => {
    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(mockConnectToEvaluation).toHaveBeenCalledWith('eval-123');
  });

  it('does not disconnect WebSocket on unmount', () => {
    const disconnect = vi.fn();
    const { unmount } = render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    unmount();

    expect(disconnect).not.toHaveBeenCalled();
  });

  it('shows determinate progress bar with completed/total', () => {
    mockProgress = { completed: 5, total: 10, currentItem: 'What is RHEL?' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('5 / 10 items')).toBeInTheDocument();
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

  it('shows completed message when evaluation is completed', () => {
    mockCurrentEvaluation = { name: 'Test Eval', status: 'completed' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Evaluation completed successfully.')).toBeInTheDocument();
  });

  it('shows failed message when evaluation failed', () => {
    mockCurrentEvaluation = { name: 'Test Eval', status: 'failed' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Evaluation failed.')).toBeInTheDocument();
  });

  it('shows fallback title when no evaluation name', () => {
    mockCurrentEvaluation = { status: 'running' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Evaluation')).toBeInTheDocument();
  });

  it('shows pending status pill', () => {
    mockCurrentEvaluation = { name: 'Test Eval', status: 'pending' };

    render(<EvaluationProgress evaluationId="eval-123" onComplete={vi.fn()} />);

    expect(screen.getByText('Pending')).toBeInTheDocument();
  });
});
