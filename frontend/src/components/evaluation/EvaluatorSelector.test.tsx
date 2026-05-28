import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EvaluatorSelector } from './EvaluatorSelector';
import { useEvaluatorStore } from '@/stores/evaluatorStore';
import type { EvaluatorInfo } from '@/types';

vi.mock('@/services/api', () => ({
  api: {
    listEvaluators: vi.fn().mockResolvedValue([]),
    getEvaluator: vi.fn(),
  },
}));

const makeEvaluator = (overrides: Partial<EvaluatorInfo> = {}): EvaluatorInfo => ({
  id: 'litellm-judge',
  name: 'LLM-as-Judge (LiteLLM)',
  description: 'Direct LLM-as-judge scoring via LiteLLM.',
  modes: ['qa', 'agent', 'rag'],
  builtin: true,
  available: true,
  defaults: { pass_threshold: 0.7 },
  config_schema: { type: 'object', properties: {} },
  ...overrides,
});

describe('EvaluatorSelector', () => {
  beforeEach(() => {
    useEvaluatorStore.setState({
      evaluators: [],
      selectedEvaluatorId: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('renders evaluator cards when evaluators are loaded', async () => {
    const evaluators = [
      makeEvaluator({ id: 'litellm-judge', name: 'LLM-as-Judge' }),
      makeEvaluator({ id: 'deepeval', name: 'DeepEval' }),
    ];
    useEvaluatorStore.setState({
      evaluators,
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
    });

    render(<EvaluatorSelector mode="qa" />);

    expect(screen.getByText('LLM-as-Judge')).toBeInTheDocument();
    expect(screen.getByText('DeepEval')).toBeInTheDocument();
  });

  it('shows evaluator description on cards', async () => {
    useEvaluatorStore.setState({
      evaluators: [makeEvaluator({ description: 'A test evaluator description' })],
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
    });

    render(<EvaluatorSelector mode="qa" />);

    expect(screen.getByText('A test evaluator description')).toBeInTheDocument();
  });

  it('displays mode badges on evaluator cards', async () => {
    useEvaluatorStore.setState({
      evaluators: [makeEvaluator({ modes: ['qa', 'rag'] })],
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
    });

    render(<EvaluatorSelector mode="qa" />);

    expect(screen.getByText('qa')).toBeInTheDocument();
    expect(screen.getByText('rag')).toBeInTheDocument();
  });

  it('displays built-in badge for builtin evaluators', async () => {
    useEvaluatorStore.setState({
      evaluators: [makeEvaluator({ builtin: true })],
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
    });

    render(<EvaluatorSelector mode="qa" />);

    expect(screen.getByText('Built-in')).toBeInTheDocument();
  });

  it('highlights selected evaluator card', async () => {
    useEvaluatorStore.setState({
      evaluators: [
        makeEvaluator({ id: 'eval-1', name: 'Evaluator 1' }),
        makeEvaluator({ id: 'eval-2', name: 'Evaluator 2' }),
      ],
      selectedEvaluatorId: 'eval-1',
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
    });

    render(<EvaluatorSelector mode="qa" />);

    const selectedCard = screen.getByText('Evaluator 1').closest('[data-slot="card"]');
    const unselectedCard = screen.getByText('Evaluator 2').closest('[data-slot="card"]');

    expect(selectedCard?.className).toContain('ring-primary');
    expect(unselectedCard?.className).not.toContain('ring-primary');
  });

  it('selects evaluator on card click', async () => {
    const user = userEvent.setup();
    const selectEvaluator = vi.fn();
    useEvaluatorStore.setState({
      evaluators: [makeEvaluator({ id: 'eval-1', name: 'Evaluator 1' })],
      selectedEvaluatorId: null,
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
      selectEvaluator,
    });

    render(<EvaluatorSelector mode="qa" />);

    const card = screen.getByText('Evaluator 1').closest('[data-slot="card"]');
    await user.click(card!);

    expect(selectEvaluator).toHaveBeenCalledWith('eval-1');
  });

  it('calls onSelect callback when evaluator is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    useEvaluatorStore.setState({
      evaluators: [makeEvaluator({ id: 'eval-1', name: 'Evaluator 1' })],
      selectedEvaluatorId: null,
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
      selectEvaluator: vi.fn(),
    });

    render(<EvaluatorSelector mode="qa" onSelect={onSelect} />);

    const card = screen.getByText('Evaluator 1').closest('[data-slot="card"]');
    await user.click(card!);

    expect(onSelect).toHaveBeenCalledWith('eval-1');
  });

  it('shows empty state when no evaluators available', async () => {
    useEvaluatorStore.setState({
      evaluators: [],
      isLoading: false,
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
    });

    render(<EvaluatorSelector mode="qa" />);

    expect(screen.getByText('No evaluators configured for this mode')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    useEvaluatorStore.setState({
      evaluators: [],
      isLoading: true,
      fetchEvaluators: vi.fn().mockReturnValue(new Promise(() => {})),
    });

    render(<EvaluatorSelector mode="qa" />);

    expect(screen.getByText('Loading evaluators...')).toBeInTheDocument();
  });

  it('shows error state with retry button', async () => {
    const fetchEvaluators = vi.fn().mockResolvedValue(undefined);
    useEvaluatorStore.setState({
      evaluators: [],
      isLoading: false,
      error: 'Something went wrong',
      fetchEvaluators,
    });

    render(<EvaluatorSelector mode="qa" />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('fetches evaluators on mount with mode parameter', async () => {
    const fetchEvaluators = vi.fn().mockResolvedValue(undefined);
    useEvaluatorStore.setState({ fetchEvaluators });

    render(<EvaluatorSelector mode="rag" />);

    await waitFor(() => {
      expect(fetchEvaluators).toHaveBeenCalledWith('rag');
    });
  });

  it('applies muted styling to unavailable evaluators', async () => {
    useEvaluatorStore.setState({
      evaluators: [makeEvaluator({ id: 'unavail', name: 'Unavailable Eval', available: false })],
      fetchEvaluators: vi.fn().mockResolvedValue(undefined),
    });

    render(<EvaluatorSelector mode="qa" />);

    const card = screen.getByText('Unavailable Eval').closest('[data-slot="card"]');
    expect(card?.className).toContain('opacity-50');
  });
});
