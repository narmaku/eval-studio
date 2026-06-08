import { render, screen } from '@testing-library/react';
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
    ssl_cert_path: null,
    tags: ['fast'],
    purpose: 'test',
    default_params: null,
    provider_type: 'litellm',
    endpoint_url: null,
    request_body_template: null,
    response_json_path: 'choices.0.message.content',
  },
  {
    id: 'provider-2',
    name: 'Model Beta',
    litellm_model: 'openai/gpt-3.5',
    api_base: null,
    has_api_key: true,
    proxy: null,
    ssl_cert_path: null,
    tags: [],
    purpose: 'test',
    default_params: null,
    provider_type: 'litellm',
    endpoint_url: null,
    request_body_template: null,
    response_json_path: 'choices.0.message.content',
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
    await user.click(removeButtons[1]!);

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

  it('does not call onChange when removing an empty slot beyond value length', async () => {
    const user = userEvent.setup();
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
    ];
    const onChange = vi.fn();
    render(
      <ContestantSelector value={contestants} onChange={onChange} />,
    );

    // Add a third slot (empty)
    await user.click(screen.getByRole('button', { name: /add contestant/i }));
    expect(screen.getByText('#3')).toBeInTheDocument();

    // Remove the third slot (index 2, which is beyond value.length of 2)
    const removeButtons = screen.getAllByRole('button', { name: /remove contestant/i });
    await user.click(removeButtons[2]!);

    // onChange should NOT be called because the slot was empty
    expect(onChange).not.toHaveBeenCalled();
  });

  it('does not add past MAX_CONTESTANTS (8) via repeated clicks', async () => {
    const user = userEvent.setup();
    const contestants: ModelEndpoint[] = Array.from({ length: 7 }, (_, i) => ({
      name: `Model ${i + 1}`,
      litellm_model: `openai/model-${i + 1}`,
    }));
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    const addButton = screen.getByRole('button', { name: /add contestant/i });
    // Should be able to add one more (7 -> 8)
    expect(addButton).not.toBeDisabled();
    await user.click(addButton);
    expect(screen.getByText('#8')).toBeInTheDocument();

    // Now should be disabled at max
    expect(addButton).toBeDisabled();
  });

  it('does not remove below MIN_CONTESTANTS (2) when only 2 remain', async () => {
    const user = userEvent.setup();
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    const removeButtons = screen.getAllByRole('button', { name: /remove contestant/i });
    // Both remove buttons should be disabled
    expect(removeButtons).toHaveLength(2);
    removeButtons.forEach((button) => {
      expect(button).toBeDisabled();
    });

    // Clicking a disabled button should not trigger onChange
    await user.click(removeButtons[0]!);
    expect(onChange).not.toHaveBeenCalled();
  });

  it('has correct aria-labels on remove buttons', () => {
    const contestants: ModelEndpoint[] = [
      { name: 'Model A', litellm_model: 'openai/a' },
      { name: 'Model B', litellm_model: 'openai/b' },
      { name: 'Model C', litellm_model: 'openai/c' },
    ];
    const onChange = vi.fn();
    render(<ContestantSelector value={contestants} onChange={onChange} />);

    expect(screen.getByLabelText('Remove contestant 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Remove contestant 2')).toBeInTheDocument();
    expect(screen.getByLabelText('Remove contestant 3')).toBeInTheDocument();
  });
});
