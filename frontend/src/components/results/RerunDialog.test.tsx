import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RerunDialog } from './RerunDialog';

const mockNavigate = vi.fn();

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock the API
vi.mock('@/services/api', () => ({
  api: {
    cloneAndRerunEvaluation: vi.fn(),
    rerunEvaluation: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockSetCurrentEvaluation = vi.fn();
const mockPersistRunningEvaluation = vi.fn();
const mockConnectToEvaluation = vi.fn();

// Mock evaluation store
vi.mock('@/stores/evaluationStore', () => ({
  useEvaluationStore: () => ({
    setCurrentEvaluation: mockSetCurrentEvaluation,
    persistRunningEvaluation: mockPersistRunningEvaluation,
    connectToEvaluation: mockConnectToEvaluation,
  }),
}));

import { api } from '@/services/api';
import { toast } from 'sonner';

const mockedApi = vi.mocked(api);
const mockedToast = vi.mocked(toast);

const baseEvaluation = {
  evaluationId: 'eval-123',
  name: 'Test Evaluation',
  mode: 'qa' as const,
  totalItems: 10,
  passRate: 0.8,
  status: 'completed' as const,
};

describe('RerunDialog', () => {
  const onOpenChange = vi.fn();
  const onSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    mockSetCurrentEvaluation.mockReset();
    mockPersistRunningEvaluation.mockReset();
    mockConnectToEvaluation.mockReset();
    mockedApi.cloneAndRerunEvaluation.mockResolvedValue({
      id: 'new-eval',
      name: 'Test Evaluation (re-run)',
      mode: 'qa',
      status: 'pending',
      dataset_id: null,
      rubric_id: null,
      config: {} as never,
      result_count: null,
      average_score: null,
      pass_rate: null,
      created_at: '',
      updated_at: '',
    });
    mockedApi.rerunEvaluation.mockResolvedValue({
      id: 'eval-123',
      name: 'Test Evaluation',
      mode: 'qa',
      status: 'pending',
      dataset_id: null,
      rubric_id: null,
      config: {} as never,
      result_count: null,
      average_score: null,
      pass_rate: null,
      created_at: '',
      updated_at: '',
    });
  });

  it('renders dialog with evaluation name and all three options', () => {
    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={baseEvaluation}
        onSuccess={onSuccess}
      />,
    );

    expect(screen.getByText('Re-run Evaluation')).toBeInTheDocument();
    expect(screen.getByText('Test Evaluation')).toBeInTheDocument();
    expect(screen.getByText('Full re-run (new evaluation)')).toBeInTheDocument();
    expect(screen.getByText('Re-run failures only (new evaluation)')).toBeInTheDocument();
    expect(screen.getByText('Re-run in place (overwrite results)')).toBeInTheDocument();
  });

  it('disables failures-only option for arena mode', () => {
    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={{ ...baseEvaluation, mode: 'arena' }}
        onSuccess={onSuccess}
      />,
    );

    const failuresButton = screen
      .getByText('Re-run failures only (new evaluation)')
      .closest('button');
    expect(failuresButton).toBeDisabled();
    expect(screen.getByText('Not available for arena evaluations')).toBeInTheDocument();
  });

  it('disables failures-only option when there are 0 failures', () => {
    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={{ ...baseEvaluation, passRate: 1.0 }}
        onSuccess={onSuccess}
      />,
    );

    const failuresButton = screen
      .getByText('Re-run failures only (new evaluation)')
      .closest('button');
    expect(failuresButton).toBeDisabled();
    expect(screen.getByText('No failed items to re-run')).toBeInTheDocument();
  });

  it('calls cloneAndRerunEvaluation with full mode on confirm', async () => {
    const user = userEvent.setup();

    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={baseEvaluation}
        onSuccess={onSuccess}
      />,
    );

    await user.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(mockedApi.cloneAndRerunEvaluation).toHaveBeenCalledWith('eval-123', 'full');
    });
    expect(mockedToast.success).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/evaluate/qa');
    expect(mockConnectToEvaluation).toHaveBeenCalledWith('new-eval');
    expect(onSuccess).toHaveBeenCalled();
  });

  it('calls cloneAndRerunEvaluation with failures_only mode when selected', async () => {
    const user = userEvent.setup();

    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={baseEvaluation}
        onSuccess={onSuccess}
      />,
    );

    await user.click(screen.getByText('Re-run failures only (new evaluation)'));
    await user.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(mockedApi.cloneAndRerunEvaluation).toHaveBeenCalledWith('eval-123', 'failures_only');
    });
  });

  it('calls rerunEvaluation when in-place option is selected', async () => {
    const user = userEvent.setup();

    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={baseEvaluation}
        onSuccess={onSuccess}
      />,
    );

    await user.click(screen.getByText('Re-run in place (overwrite results)'));
    await user.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(mockedApi.rerunEvaluation).toHaveBeenCalledWith('eval-123');
    });
    expect(mockedToast.success).toHaveBeenCalled();
  });

  it('shows error toast on API failure', async () => {
    const user = userEvent.setup();
    mockedApi.cloneAndRerunEvaluation.mockRejectedValue(new Error('Server error'));

    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={baseEvaluation}
        onSuccess={onSuccess}
      />,
    );

    await user.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(mockedToast.error).toHaveBeenCalledWith('Failed to start re-run: Server error');
    });
  });

  it('closes dialog when Cancel is clicked', async () => {
    const user = userEvent.setup();

    render(
      <RerunDialog
        open={true}
        onOpenChange={onOpenChange}
        evaluation={baseEvaluation}
        onSuccess={onSuccess}
      />,
    );

    await user.click(screen.getByText('Cancel'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
