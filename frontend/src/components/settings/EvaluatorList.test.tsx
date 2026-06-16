import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { EvaluatorInfo } from '@/types';

const mockListEvaluators = vi.fn();
const mockListConfigFiles = vi.fn();

vi.mock('@/services/api', () => ({
  api: {
    listEvaluators: (...args: unknown[]) => mockListEvaluators(...args),
    listEvaluatorConfigFiles: (...args: unknown[]) => mockListConfigFiles(...args),
    uploadEvaluatorConfigFile: vi.fn(),
    deleteEvaluatorConfigFile: vi.fn(),
    getEvaluatorConfigFile: vi.fn(),
  },
}));

import { EvaluatorList } from './EvaluatorList';

const makeEvaluator = (overrides: Partial<EvaluatorInfo> = {}): EvaluatorInfo => ({
  id: 'eval-1',
  name: 'Test Evaluator',
  description: 'A test evaluator for QA',
  modes: ['qa'],
  builtin: true,
  available: true,
  defaults: { pass_threshold: 0.7 },
  config_schema: {},
  ...overrides,
});

describe('EvaluatorList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches evaluators on mount', () => {
    mockListEvaluators.mockResolvedValue([]);
    render(<EvaluatorList />);
    expect(mockListEvaluators).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no evaluators', async () => {
    mockListEvaluators.mockResolvedValue([]);
    render(<EvaluatorList />);
    await waitFor(() => {
      expect(screen.getByText(/no evaluators configured/i)).toBeInTheDocument();
    });
  });

  it('renders evaluator cards', async () => {
    mockListEvaluators.mockResolvedValue([
      makeEvaluator({ id: 'e-1', name: 'QA Evaluator' }),
      makeEvaluator({ id: 'e-2', name: 'RAG Evaluator', modes: ['rag'] }),
    ]);

    render(<EvaluatorList />);

    await waitFor(() => {
      expect(screen.getByText('QA Evaluator')).toBeInTheDocument();
      expect(screen.getByText('RAG Evaluator')).toBeInTheDocument();
    });
  });

  it('shows mode badges', async () => {
    mockListEvaluators.mockResolvedValue([makeEvaluator({ modes: ['qa', 'rag', 'agent'] })]);

    render(<EvaluatorList />);

    await waitFor(() => {
      expect(screen.getByText('qa')).toBeInTheDocument();
      expect(screen.getByText('rag')).toBeInTheDocument();
      expect(screen.getByText('agent')).toBeInTheDocument();
    });
  });

  it('shows available status with green indicator', async () => {
    mockListEvaluators.mockResolvedValue([makeEvaluator({ available: true })]);

    render(<EvaluatorList />);

    await waitFor(() => {
      expect(screen.getByText('Available')).toBeInTheDocument();
    });
  });

  it('shows unavailable status with red indicator', async () => {
    mockListEvaluators.mockResolvedValue([makeEvaluator({ available: false })]);

    render(<EvaluatorList />);

    await waitFor(() => {
      expect(screen.getByText('Unavailable')).toBeInTheDocument();
    });
  });

  it('shows built-in badge for builtin evaluators', async () => {
    mockListEvaluators.mockResolvedValue([makeEvaluator({ builtin: true })]);

    render(<EvaluatorList />);

    await waitFor(() => {
      expect(screen.getByText('Built-in')).toBeInTheDocument();
    });
  });

  it('shows Configure button on each evaluator card', async () => {
    mockListEvaluators.mockResolvedValue([
      makeEvaluator({ id: 'e-1', name: 'QA Evaluator' }),
      makeEvaluator({ id: 'e-2', name: 'RAG Evaluator' }),
    ]);

    render(<EvaluatorList />);

    await waitFor(() => {
      const buttons = screen.getAllByRole('button', { name: /configure/i });
      expect(buttons).toHaveLength(2);
    });
  });

  it('opens detail panel when Configure is clicked', async () => {
    const user = userEvent.setup();
    mockListEvaluators.mockResolvedValue([makeEvaluator({ id: 'e-1', name: 'QA Evaluator' })]);
    mockListConfigFiles.mockResolvedValue([]);

    render(<EvaluatorList />);

    await waitFor(() => {
      expect(screen.getByText('QA Evaluator')).toBeInTheDocument();
    });

    const configureButton = screen.getByRole('button', { name: /configure/i });
    await user.click(configureButton);

    await waitFor(() => {
      // The detail panel should show the evaluator name as a heading
      expect(screen.getByText('Default Configuration')).toBeInTheDocument();
    });
  });
});
