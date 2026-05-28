import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGenerateRubric = vi.fn();
const mockListProviders = vi.fn();

vi.mock('@/stores/rubricStore', () => ({
  useRubricStore: (selector?: unknown) => {
    const state = {
      generateRubric: mockGenerateRubric,
    };
    if (typeof selector === 'function') {
      return (selector as (s: typeof state) => unknown)(state);
    }
    return state;
  },
}));

vi.mock('@/services/api', () => ({
  api: {
    listProviders: (...args: unknown[]) => mockListProviders(...args),
  },
}));

import { RubricGenerateDialog } from './RubricGenerateDialog';

const providerList = [
  {
    id: 'openai-gpt4',
    name: 'OpenAI GPT-4',
    litellm_model: 'gpt-4',
    api_base: null,
    has_api_key: true,
    proxy: null,
    tags: [],
    purpose: 'judge',
  },
];

describe('RubricGenerateDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListProviders.mockResolvedValue(providerList);
  });

  it('renders nothing when closed', () => {
    render(<RubricGenerateDialog open={false} onOpenChange={vi.fn()} />);
    expect(screen.queryByText(/generate rubric/i)).not.toBeInTheDocument();
  });

  it('renders dialog content when open', () => {
    render(<RubricGenerateDialog open={true} onOpenChange={vi.fn()} />);
    expect(screen.getByText('Generate Rubric')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/describe what you want/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^generate$/i })).toBeInTheDocument();
  });

  it('disables generate button when description is empty', () => {
    render(<RubricGenerateDialog open={true} onOpenChange={vi.fn()} />);
    const btn = screen.getByRole('button', { name: /^generate$/i });
    expect(btn).toBeDisabled();
  });

  it('loads providers on open', async () => {
    render(<RubricGenerateDialog open={true} onOpenChange={vi.fn()} />);
    await waitFor(() => {
      expect(mockListProviders).toHaveBeenCalled();
    });
  });

  it('has description and sample data text areas', async () => {
    const user = userEvent.setup();
    render(<RubricGenerateDialog open={true} onOpenChange={vi.fn()} />);

    const descArea = screen.getByPlaceholderText(/describe what you want/i);
    await user.type(descArea, 'Test description');
    expect(descArea).toHaveValue('Test description');

    const sampleArea = screen.getByPlaceholderText(/paste sample/i);
    await user.type(sampleArea, 'Q: What? A: This.');
    expect(sampleArea).toHaveValue('Q: What? A: This.');
  });

  it('has a provider selector combobox', () => {
    render(<RubricGenerateDialog open={true} onOpenChange={vi.fn()} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('renders provider label and all form sections', () => {
    render(<RubricGenerateDialog open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByText('Generate Rubric')).toBeInTheDocument();
    expect(screen.getByText('Provider')).toBeInTheDocument();
    expect(screen.getByText(/sample data/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });
});
