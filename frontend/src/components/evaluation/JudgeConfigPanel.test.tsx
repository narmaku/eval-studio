import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JudgeConfigPanel } from './JudgeConfigPanel';

const mockListProviders = vi.fn();
const mockListRubrics = vi.fn();
const mockListProviderModels = vi.fn();

vi.mock('@/services/api', () => ({
  api: {
    listProviders: (...args: unknown[]) => mockListProviders(...args),
    listRubrics: (...args: unknown[]) => mockListRubrics(...args),
    listProviderModels: (...args: unknown[]) => mockListProviderModels(...args),
  },
}));

const provider = {
  id: 'p1',
  name: 'OpenAI',
  default_model: 'gpt-4',
  api_base: null,
  has_api_key: true,
  proxy: null,
  ssl_cert_path: null,
  ssl_client_key: null,
  tags: ['openai'],
  default_params: null,
  provider_type: 'standard',
  endpoint_url: null,
  request_body_template: '',
  response_json_path: '',
  single_model: false,
  rate_limited: false,
  rate_limits: null,
};

const singleModelProvider = {
  ...provider,
  id: 'p2',
  name: 'Single Model',
  single_model: true,
};

const rubric = {
  id: 'r1',
  name: 'Accuracy Rubric',
  description: 'Test rubric',
  dimensions: [
    { name: 'accuracy', weight: 2, description: 'Factual accuracy' },
    { name: 'clarity', weight: 1, description: 'Clarity' },
  ],
  pass_threshold: 0.8,
  aggregation: 'weighted_average',
  prompt_template: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('JudgeConfigPanel', () => {
  const onChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockListProviders.mockResolvedValue([provider]);
    mockListRubrics.mockResolvedValue({
      items: [rubric],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
    mockListProviderModels.mockResolvedValue([
      { id: 'gpt-4', owned_by: 'openai' },
      { id: 'gpt-4o', owned_by: 'openai' },
      { id: 'gpt-3.5-turbo', owned_by: 'openai' },
    ]);
  });

  it('renders providers and rubric selector', async () => {
    render(<JudgeConfigPanel value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    expect(screen.getByText('Scoring Rubric (optional)')).toBeInTheDocument();
  });

  it('shows rubric details when selected', async () => {
    render(<JudgeConfigPanel value={{ provider_id: 'p1', rubric_id: 'r1' }} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText(/2 dimensions/)).toBeInTheDocument();
    });

    expect(screen.getByText(/weighted_average/)).toBeInTheDocument();
    expect(screen.getByText(/threshold 0.8/)).toBeInTheDocument();
    expect(screen.getByText(/accuracy \(w=2\)/)).toBeInTheDocument();
    expect(screen.getByText(/clarity \(w=1\)/)).toBeInTheDocument();
  });

  it('calls onChange with model and rubric_id when provider selected', async () => {
    const user = userEvent.setup();
    render(<JudgeConfigPanel value={{ rubric_id: 'r1' }} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    await user.click(screen.getByText('OpenAI'));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ provider_id: 'p1', model: 'gpt-4', rubric_id: 'r1' }),
    );
  });

  it('fetches models when provider is selected', async () => {
    const user = userEvent.setup();
    render(<JudgeConfigPanel value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    await user.click(screen.getByText('OpenAI'));

    expect(mockListProviderModels).toHaveBeenCalledWith('p1');
  });

  it('shows model dropdown after provider selection', async () => {
    const user = userEvent.setup();
    render(<JudgeConfigPanel value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    await user.click(screen.getByText('OpenAI'));

    await waitFor(() => {
      expect(screen.getByText('Model')).toBeInTheDocument();
    });
  });

  it('does not show model dropdown for single_model providers', async () => {
    mockListProviders.mockResolvedValue([singleModelProvider]);
    const user = userEvent.setup();
    render(<JudgeConfigPanel value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText('Single Model')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Single Model'));

    expect(screen.queryByText('Model')).not.toBeInTheDocument();
    expect(mockListProviderModels).not.toHaveBeenCalled();
  });

  it('does not show rubric section when no rubrics exist', async () => {
    mockListRubrics.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      pages: 1,
    });

    render(<JudgeConfigPanel value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    expect(screen.queryByText('Scoring Rubric (optional)')).not.toBeInTheDocument();
  });

  it('shows criteria count in dimension badges', async () => {
    const rubricWithCriteria = {
      ...rubric,
      dimensions: [
        {
          name: 'accuracy',
          weight: 2,
          description: 'Factual accuracy',
          criteria: [
            { name: 'factual', criterion: 'Is factual', weight: 1 },
            { name: 'complete', criterion: 'Is complete', weight: 1 },
          ],
        },
        { name: 'clarity', weight: 1, description: 'Clarity' },
      ],
    };
    mockListRubrics.mockResolvedValue({
      items: [rubricWithCriteria],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });

    render(<JudgeConfigPanel value={{ provider_id: 'p1', rubric_id: 'r1' }} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText(/accuracy \(w=2, 2c\)/)).toBeInTheDocument();
    });

    // clarity has no criteria, so no criteria count suffix
    expect(screen.getByText(/clarity \(w=1\)/)).toBeInTheDocument();
  });
});
