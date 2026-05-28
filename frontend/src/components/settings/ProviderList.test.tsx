import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Provider } from '@/types';

const mockListProviders = vi.fn();

vi.mock('@/services/api', () => ({
  api: {
    listProviders: (...args: unknown[]) => mockListProviders(...args),
  },
}));

import { ProviderList } from './ProviderList';

const makeProvider = (overrides: Partial<Provider> = {}): Provider => ({
  id: 'p-1',
  name: 'Test Provider',
  litellm_model: 'gpt-4',
  api_base: 'https://api.openai.com/v1',
  has_api_key: true,
  proxy: null,
  tags: ['general'],
  purpose: 'test',
  ...overrides,
});

describe('ProviderList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches providers on mount', () => {
    mockListProviders.mockResolvedValue([]);
    render(<ProviderList />);
    expect(mockListProviders).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no providers', async () => {
    mockListProviders.mockResolvedValue([]);
    render(<ProviderList />);
    await waitFor(() => {
      expect(screen.getByText(/no providers configured/i)).toBeInTheDocument();
    });
  });

  it('renders provider rows', async () => {
    mockListProviders.mockResolvedValue([
      makeProvider({ id: 'p-1', name: 'OpenAI', litellm_model: 'gpt-4' }),
      makeProvider({ id: 'p-2', name: 'Anthropic', litellm_model: 'claude-3' }),
    ]);

    render(<ProviderList />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
    });
  });

  it('shows model name', async () => {
    mockListProviders.mockResolvedValue([
      makeProvider({ litellm_model: 'gpt-4-turbo' }),
    ]);

    render(<ProviderList />);

    await waitFor(() => {
      expect(screen.getByText('gpt-4-turbo')).toBeInTheDocument();
    });
  });

  it('shows purpose badge', async () => {
    mockListProviders.mockResolvedValue([
      makeProvider({ purpose: 'judge' }),
    ]);

    render(<ProviderList />);

    await waitFor(() => {
      expect(screen.getByText('judge')).toBeInTheDocument();
    });
  });
});
