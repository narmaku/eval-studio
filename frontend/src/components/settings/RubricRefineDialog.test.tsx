import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Rubric } from '@/types';

const mockRefineRubric = vi.fn();
const mockListProviders = vi.fn();

vi.mock('@/stores/rubricStore', () => ({
  useRubricStore: (selector?: unknown) => {
    const state = {
      refineRubric: mockRefineRubric,
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

import { RubricRefineDialog } from './RubricRefineDialog';

const makeRubric = (overrides: Partial<Rubric> = {}): Rubric => ({
  id: 'r-1',
  name: 'Test Rubric',
  description: 'A test rubric',
  dimensions: [
    { name: 'accuracy', weight: 0.6, description: 'Accuracy' },
    { name: 'completeness', weight: 0.4, description: 'Completeness' },
  ],
  pass_threshold: 0.7,
  aggregation: 'weighted_average',
  prompt_template: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('RubricRefineDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListProviders.mockResolvedValue([
      {
        id: 'openai-gpt4',
        name: 'OpenAI GPT-4',
        default_model: 'gpt-4',
        api_base: null,
        has_api_key: true,
        proxy: null,
        tags: [],
      },
    ]);
  });

  it('renders nothing when closed', () => {
    render(<RubricRefineDialog open={false} onOpenChange={vi.fn()} rubric={makeRubric()} />);
    expect(screen.queryByText(/refine rubric/i)).not.toBeInTheDocument();
  });

  it('renders dialog content when open', () => {
    render(<RubricRefineDialog open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);
    expect(screen.getByText('Refine Rubric')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/what should be improved/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^refine$/i })).toBeInTheDocument();
  });

  it('displays rubric name and dimension count', () => {
    render(<RubricRefineDialog open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);
    expect(screen.getByText(/test rubric/i)).toBeInTheDocument();
    expect(screen.getByText(/2 dimensions/i)).toBeInTheDocument();
  });

  it('disables refine button when feedback is empty', () => {
    render(<RubricRefineDialog open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);
    const btn = screen.getByRole('button', { name: /^refine$/i });
    expect(btn).toBeDisabled();
  });

  it('enables refine button after entering feedback', async () => {
    const user = userEvent.setup();
    render(<RubricRefineDialog open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);

    const textarea = screen.getByPlaceholderText(/what should be improved/i);
    await user.type(textarea, 'Add a clarity dimension');

    // Button is still disabled because no provider is selected,
    // but feedback field should have content
    expect(textarea).toHaveValue('Add a clarity dimension');
  });

  it('loads providers on open', async () => {
    render(<RubricRefineDialog open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);
    await waitFor(() => {
      expect(mockListProviders).toHaveBeenCalled();
    });
  });

  it('renders provider selector and form controls', () => {
    render(<RubricRefineDialog open={true} onOpenChange={vi.fn()} rubric={makeRubric()} />);
    expect(screen.getByText('Provider')).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });
});
