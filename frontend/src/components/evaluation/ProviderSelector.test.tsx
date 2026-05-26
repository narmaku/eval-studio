import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProviderSelector } from './ProviderSelector';
import type { Provider } from '@/types';

const mockProviders: Provider[] = [
  {
    id: 'rls-staging',
    name: 'RLS Staging',
    litellm_model: 'openai/gpt-4o',
    api_base: 'https://staging.example.com',
    has_api_key: true,
    proxy: null,
    tags: ['staging'],
    purpose: 'test',
  },
  {
    id: 'rls-prod',
    name: 'RLS Production',
    litellm_model: 'openai/gpt-4o',
    api_base: null,
    has_api_key: false,
    proxy: 'http://proxy.example.com',
    tags: ['prod', 'v2'],
    purpose: 'test',
  },
];

// vi.hoisted lets us create the mock fn before vi.mock is hoisted
const listProvidersMock = vi.hoisted(() => vi.fn());

vi.mock('@/services/api', () => ({
  api: {
    listProviders: listProvidersMock,
  },
}));

describe('ProviderSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    listProvidersMock.mockReturnValue(new Promise(() => {}));

    const onChange = vi.fn();
    render(<ProviderSelector value={undefined} onChange={onChange} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toBeInTheDocument();
    expect(trigger).toBeDisabled();
    expect(screen.getByText('Loading providers...')).toBeInTheDocument();
  });

  it('renders provider dropdown after API response', async () => {
    listProvidersMock.mockResolvedValue(mockProviders);

    const onChange = vi.fn();
    render(<ProviderSelector value={undefined} onChange={onChange} />);

    await waitFor(() => {
      const trigger = screen.getByRole('combobox');
      expect(trigger).not.toBeDisabled();
    });

    // Trigger should show placeholder
    expect(screen.getByText('Select a provider...')).toBeInTheDocument();
  });

  it('gracefully handles API failure and shows custom fields', async () => {
    listProvidersMock.mockRejectedValue(new Error('Network error'));

    const onChange = vi.fn();
    render(<ProviderSelector value={undefined} onChange={onChange} />);

    // After API fails, custom fields should appear
    await waitFor(() => {
      expect(screen.getByLabelText('Name')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('LiteLLM Model')).toBeInTheDocument();
    expect(screen.getByLabelText('API Base URL (optional)')).toBeInTheDocument();

    // The select dropdown should not be shown when API failed
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('calls onChange with custom fields on blur', async () => {
    listProvidersMock.mockRejectedValue(new Error('Network error'));

    const onChange = vi.fn();
    render(<ProviderSelector value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Name')).toBeInTheDocument();
    });

    const user = userEvent.setup();

    const nameInput = screen.getByLabelText('Name');
    const modelInput = screen.getByLabelText('LiteLLM Model');

    await user.type(nameInput, 'My Model');
    await user.type(modelInput, 'openai/gpt-4o');

    // Blur the model input to trigger onChange
    fireEvent.blur(modelInput);

    expect(onChange).toHaveBeenCalledWith({
      name: 'My Model',
      litellm_model: 'openai/gpt-4o',
      api_base: undefined,
    });
  });

  it('does not call onChange when custom fields are incomplete', async () => {
    listProvidersMock.mockRejectedValue(new Error('Network error'));

    const onChange = vi.fn();
    render(<ProviderSelector value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Name')).toBeInTheDocument();
    });

    const user = userEvent.setup();

    // Only fill name, leave model empty
    const nameInput = screen.getByLabelText('Name');
    await user.type(nameInput, 'My Model');
    fireEvent.blur(nameInput);

    // onChange should NOT be called because model is still empty
    expect(onChange).not.toHaveBeenCalled();
  });

  it('disables trigger when disabled prop is true', async () => {
    listProvidersMock.mockResolvedValue(mockProviders);

    const onChange = vi.fn();
    render(<ProviderSelector value={undefined} onChange={onChange} disabled />);

    await waitFor(() => {
      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
    });
  });

  it('renders with pre-selected provider value', async () => {
    listProvidersMock.mockResolvedValue(mockProviders);

    const onChange = vi.fn();
    render(
      <ProviderSelector
        value={{
          provider_id: 'rls-staging',
          name: 'RLS Staging',
          litellm_model: 'openai/gpt-4o',
          api_base: 'https://staging.example.com',
        }}
        onChange={onChange}
      />,
    );

    await waitFor(() => {
      const trigger = screen.getByRole('combobox');
      expect(trigger).not.toBeDisabled();
    });
  });

  it('renders custom fields when no providers are available', async () => {
    listProvidersMock.mockResolvedValue([]);

    const onChange = vi.fn();
    render(<ProviderSelector value={undefined} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Name')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('LiteLLM Model')).toBeInTheDocument();
  });
});
