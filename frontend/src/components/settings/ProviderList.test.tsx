import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Provider } from '@/types';

const mockFetchProviders = vi.fn();
const mockDeleteProvider = vi.fn();

const makeProvider = (overrides: Partial<Provider> = {}): Provider => ({
  id: 'p-1',
  name: 'Test Provider',
  litellm_model: 'gpt-4',
  api_base: 'https://api.openai.com/v1',
  has_api_key: true,
  proxy: null,
  ssl_cert_path: null,
  tags: ['general'],
  purpose: 'test',
  default_params: null,
  provider_type: 'litellm',
  endpoint_url: null,
  request_body_template: null,
  response_json_path: 'choices.0.message.content',
  ...overrides,
});

let storeState: {
  providers: Provider[];
  isLoading: boolean;
  error: string | null;
  fetchProviders: typeof mockFetchProviders;
  deleteProvider: typeof mockDeleteProvider;
  createProvider: ReturnType<typeof vi.fn>;
  updateProvider: ReturnType<typeof vi.fn>;
};

const defaultStore = {
  providers: [] as Provider[],
  isLoading: false,
  error: null,
  fetchProviders: mockFetchProviders,
  deleteProvider: mockDeleteProvider,
  createProvider: vi.fn(),
  updateProvider: vi.fn(),
};

vi.mock('@/stores/providerStore', () => ({
  useProviderStore: (selector?: unknown) => {
    if (typeof selector === 'function') {
      return (selector as (s: typeof storeState) => unknown)(storeState);
    }
    return storeState;
  },
}));

// Stub ProviderForm to avoid Sheet rendering complexity in this test
vi.mock('./ProviderForm', () => ({
  ProviderForm: ({
    open,
    provider,
  }: {
    open: boolean;
    provider?: Provider;
    onOpenChange: (v: boolean) => void;
    onSaved?: () => void;
  }) =>
    open ? (
      <div data-testid="provider-form">
        {provider ? `editing ${provider.name}` : 'creating new'}
      </div>
    ) : null,
}));

import { ProviderList } from './ProviderList';

describe('ProviderList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState = { ...defaultStore };
  });

  it('calls fetchProviders on mount', () => {
    render(<ProviderList />);
    expect(mockFetchProviders).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no providers', () => {
    render(<ProviderList />);
    expect(screen.getByText(/no providers configured/i)).toBeInTheDocument();
  });

  it('renders provider rows', () => {
    storeState = {
      ...defaultStore,
      providers: [
        makeProvider({ id: 'p-1', name: 'OpenAI' }),
        makeProvider({ id: 'p-2', name: 'Anthropic' }),
      ],
    };
    render(<ProviderList />);
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('shows model name', () => {
    storeState = {
      ...defaultStore,
      providers: [makeProvider({ litellm_model: 'gpt-4-turbo' })],
    };

    render(<ProviderList />);
    expect(screen.getByText('gpt-4-turbo')).toBeInTheDocument();
  });

  it('shows purpose badge', () => {
    storeState = {
      ...defaultStore,
      providers: [makeProvider({ purpose: 'judge' })],
    };

    render(<ProviderList />);
    expect(screen.getByText('judge')).toBeInTheDocument();
  });

  it('shows edit/delete buttons for all providers', () => {
    storeState = {
      ...defaultStore,
      providers: [makeProvider({ id: 'p-1', name: 'My Provider' })],
    };
    render(<ProviderList />);
    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  it('renders New Provider button', () => {
    render(<ProviderList />);
    expect(screen.getByRole('button', { name: /new provider/i })).toBeInTheDocument();
  });

  it('filters providers by name', async () => {
    const user = userEvent.setup();
    storeState = {
      ...defaultStore,
      providers: [
        makeProvider({ id: 'p-1', name: 'OpenAI Model' }),
        makeProvider({ id: 'p-2', name: 'Anthropic Model' }),
      ],
    };
    render(<ProviderList />);

    const filterInput = screen.getByPlaceholderText(/filter/i);
    await user.type(filterInput, 'OpenAI');

    expect(screen.getByText('OpenAI Model')).toBeInTheDocument();
    expect(screen.queryByText('Anthropic Model')).not.toBeInTheDocument();
  });

  it('opens form on New Provider click', async () => {
    const user = userEvent.setup();
    render(<ProviderList />);

    await user.click(screen.getByRole('button', { name: /new provider/i }));

    expect(screen.getByTestId('provider-form')).toBeInTheDocument();
    expect(screen.getByText('creating new')).toBeInTheDocument();
  });

  it('opens form in edit mode on Edit click', async () => {
    const user = userEvent.setup();
    storeState = {
      ...defaultStore,
      providers: [makeProvider({ id: 'p-1', name: 'My Provider' })],
    };
    render(<ProviderList />);

    await user.click(screen.getByRole('button', { name: /edit/i }));

    expect(screen.getByTestId('provider-form')).toBeInTheDocument();
    expect(screen.getByText('editing My Provider')).toBeInTheDocument();
  });
});
