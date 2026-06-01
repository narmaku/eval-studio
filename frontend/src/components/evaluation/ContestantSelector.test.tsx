import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ContestantSelector } from './ContestantSelector';
import type { ModelEndpoint, Provider } from '@/types';

const mockProviders: Provider[] = [
  {
    id: 'provider-1',
    name: 'Model Alpha',
    litellm_model: 'openai/gpt-4o',
    api_base: 'https://alpha.example.com',
    has_api_key: true,
    proxy: null,
    tags: ['fast'],
    purpose: 'test',
    source: 'yaml',
    created_at: null,
    updated_at: null,
  },
  {
    id: 'provider-2',
    name: 'Model Beta',
    litellm_model: 'openai/gpt-3.5',
    api_base: null,
    has_api_key: true,
    proxy: null,
    tags: [],
    purpose: 'test',
    source: 'yaml',
    created_at: null,
    updated_at: null,
  },
];

const listProvidersMock = vi.hoisted(() => vi.fn());
const listProviderModelsMock = vi.hoisted(() => vi.fn());

vi.mock('@/services/api', () => ({
  api: {
    listProviders: listProvidersMock,
    listProviderModels: listProviderModelsMock,
  },
}));

describe('ContestantSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listProvidersMock.mockResolvedValue(mockProviders);
    listProviderModelsMock.mockResolvedValue([]);
  });

  it('renders with 2 empty contestant slots by default', () => {
    const onChange = vi.fn();
    render(<ContestantSelector value={[]} onChange={onChange} />);

    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add contestant/i })).toBeInTheDocument();
  });

  it('renders an add contestant button', () => {
    const onChange = vi.fn();
    render(<ContestantSelector value={[]} onChange={onChange} />);

    const addButton = screen.getByRole('button', { name: /add contestant/i });
    expect(addButton).toBeInTheDocument();
    expect(addButton).not.toBeDisabled();
  });

  it('adds a new contestant slot when add button is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ContestantSelector value={[]} onChange={onChange} />);

    await user.click(screen.getByRole('button', { name: /add contestant/i }));

    // Should now show 3 contestant slots
    expect(screen.getByText('#3')).toBeInTheDocument();
  });

  it('disables add button at max 8 contestants', () => {
    const contestants: ModelEndpoint[] = Array.from({ length: 8 }, (_, i) => ({
      name: `Model ${i + 1}`,
      litellm_model: `openai/model-${i + 1}`,
    }));
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    const addButton = screen.getByRole('button', { name: /add contestant/i });
    expect(addButton).toBeDisabled();
  });

  it('has remove buttons for each contestant', () => {
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
      { name: 'Model C', litellm_model: 'openai/c' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    expect(removeButtons).toHaveLength(3);
  });

  it('disables remove buttons when only 2 contestants remain', () => {
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    removeButtons.forEach((button) => {
      expect(button).toBeDisabled();
    });
  });

  it('calls onChange when removing a contestant with 3+', async () => {
    const user = userEvent.setup();
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
      { name: 'Model C', litellm_model: 'openai/c' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    // Remove the second contestant
    await user.click(removeButtons[1]);

    expect(onChange).toHaveBeenCalledWith([
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model C', litellm_model: 'openai/c' },
    ]);
  });

  it('shows contestant number badges', () => {
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
      { name: 'Model C', litellm_model: 'openai/c' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
    expect(screen.getByText('#3')).toBeInTheDocument();
  });

  it('renders a ProviderSelector for each contestant', () => {
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a', provider_id: 'provider-1' },
      { name: 'Model B', litellm_model: 'openai/b', provider_id: 'provider-2' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    // Each contestant card should have a ProviderSelector which renders a Card with "Model / Provider"
    const providerCards = screen.getAllByText('Model / Provider');
    expect(providerCards).toHaveLength(2);
  });

  it('disables all controls when disabled prop is true', () => {
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
      { name: 'Model C', litellm_model: 'openai/c' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} disabled />);

    const addButton = screen.getByRole('button', { name: /add contestant/i });
    expect(addButton).toBeDisabled();

    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    removeButtons.forEach((button) => {
      expect(button).toBeDisabled();
    });
  });
});
