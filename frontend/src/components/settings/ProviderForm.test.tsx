import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Provider } from '@/types';

const mockCreateProvider = vi.fn();
const mockUpdateProvider = vi.fn();

vi.mock('@/stores/providerStore', () => ({
  useProviderStore: (selector?: unknown) => {
    const state = {
      createProvider: mockCreateProvider,
      updateProvider: mockUpdateProvider,
    };
    if (typeof selector === 'function') {
      return (selector as (s: typeof state) => unknown)(state);
    }
    return state;
  },
}));

import { ProviderForm } from './ProviderForm';

const makeProvider = (overrides: Partial<Provider> = {}): Provider => ({
  id: 'p-1',
  name: 'Existing Provider',
  litellm_model: 'openai/gpt-4',
  api_base: 'https://api.example.com',
  has_api_key: true,
  proxy: null,
  ssl_cert_path: null,
  tags: ['fast'],
  purpose: 'test',
  default_params: null,
  provider_type: 'litellm',
  endpoint_url: null,
  request_format: 'openai',
  response_json_path: 'choices.0.message.content',
  ...overrides,
});

describe('ProviderForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form fields when open', () => {
    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/litellm model/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api base/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api key env/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/proxy/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/purpose/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tags/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/provider type/i)).toBeInTheDocument();
  });

  it('renders "New Provider" title in create mode', () => {
    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);
    expect(screen.getByText('New Provider')).toBeInTheDocument();
  });

  it('renders "Edit Provider" title in edit mode', () => {
    render(<ProviderForm open={true} onOpenChange={vi.fn()} provider={makeProvider()} />);
    expect(screen.getByText('Edit Provider')).toBeInTheDocument();
  });

  it('populates form with provider data in edit mode', () => {
    render(<ProviderForm open={true} onOpenChange={vi.fn()} provider={makeProvider()} />);

    expect(screen.getByLabelText(/name/i)).toHaveValue('Existing Provider');
    expect(screen.getByLabelText(/litellm model/i)).toHaveValue('openai/gpt-4');
    expect(screen.getByLabelText(/api base/i)).toHaveValue('https://api.example.com');
  });

  it('validates: rejects empty name', async () => {
    const user = userEvent.setup();
    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

    // Fill in model but not name
    await user.type(screen.getByLabelText(/litellm model/i), 'openai/gpt-4');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    expect(mockCreateProvider).not.toHaveBeenCalled();
  });

  it('validates: rejects empty model for litellm type', async () => {
    const user = userEvent.setup();
    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

    // Fill in name but not model
    await user.type(screen.getByLabelText(/name/i), 'My Provider');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByText(/litellm model is required/i)).toBeInTheDocument();
    expect(mockCreateProvider).not.toHaveBeenCalled();
  });

  it('calls createProvider on save in create mode', async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    const onOpenChange = vi.fn();
    mockCreateProvider.mockResolvedValue(makeProvider());

    render(<ProviderForm open={true} onOpenChange={onOpenChange} onSaved={onSaved} />);

    await user.type(screen.getByLabelText(/name/i), 'New Provider');
    await user.type(screen.getByLabelText(/litellm model/i), 'openai/gpt-4');

    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockCreateProvider).toHaveBeenCalledTimes(1);
    expect(mockCreateProvider).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'New Provider',
        litellm_model: 'openai/gpt-4',
        provider_type: 'litellm',
      }),
    );
  });

  it('calls updateProvider on save in edit mode', async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    mockUpdateProvider.mockResolvedValue(makeProvider({ name: 'Updated' }));

    render(
      <ProviderForm
        open={true}
        onOpenChange={vi.fn()}
        provider={makeProvider()}
        onSaved={onSaved}
      />,
    );

    const nameInput = screen.getByLabelText(/name/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated');

    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockUpdateProvider).toHaveBeenCalledTimes(1);
    expect(mockUpdateProvider).toHaveBeenCalledWith(
      'p-1',
      expect.objectContaining({ name: 'Updated' }),
    );
  });

  describe('custom provider type', () => {
    it('hides LiteLLM Model field when custom type is selected', async () => {
      const user = userEvent.setup();
      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      // Initially LiteLLM Model should be visible
      expect(screen.getByLabelText(/litellm model/i)).toBeInTheDocument();

      // Select "Custom API" type
      await user.click(screen.getByLabelText(/provider type/i));
      await user.click(screen.getByText('Custom API'));

      // LiteLLM Model should be hidden
      expect(screen.queryByLabelText(/litellm model/i)).not.toBeInTheDocument();
    });

    it('shows custom fields when custom type is selected', async () => {
      const user = userEvent.setup();
      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      // Custom fields should not be visible initially
      expect(screen.queryByLabelText(/endpoint url/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/request format/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/response json path/i)).not.toBeInTheDocument();

      // Select "Custom API" type
      await user.click(screen.getByLabelText(/provider type/i));
      await user.click(screen.getByText('Custom API'));

      // Custom fields should be visible
      expect(screen.getByLabelText(/endpoint url/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/request format/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/response json path/i)).toBeInTheDocument();
    });

    it('validates: rejects empty endpoint URL for custom type', async () => {
      const user = userEvent.setup();
      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      // Select "Custom API" type
      await user.click(screen.getByLabelText(/provider type/i));
      await user.click(screen.getByText('Custom API'));

      // Fill name but not endpoint URL
      await user.type(screen.getByLabelText(/name/i), 'My Custom Provider');
      await user.click(screen.getByRole('button', { name: /save/i }));

      expect(screen.getByText(/endpoint url is required/i)).toBeInTheDocument();
      expect(mockCreateProvider).not.toHaveBeenCalled();
    });

    it('creates custom provider with correct fields', async () => {
      const user = userEvent.setup();
      mockCreateProvider.mockResolvedValue(
        makeProvider({
          provider_type: 'custom',
          endpoint_url: 'https://example.com/api/v1/infer',
        }),
      );

      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      // Select "Custom API" type
      await user.click(screen.getByLabelText(/provider type/i));
      await user.click(screen.getByText('Custom API'));

      await user.type(screen.getByLabelText(/name/i), 'RLS Staging');
      await user.type(
        screen.getByLabelText(/endpoint url/i),
        'https://example.com/api/v1/infer',
      );

      // Select rls_infer format
      await user.click(screen.getByLabelText(/request format/i));
      await user.click(screen.getByText('RLS Infer (question field)'));

      // Set response path
      const pathInput = screen.getByLabelText(/response json path/i);
      await user.clear(pathInput);
      await user.type(pathInput, 'data.text');

      await user.click(screen.getByRole('button', { name: /save/i }));

      expect(mockCreateProvider).toHaveBeenCalledTimes(1);
      expect(mockCreateProvider).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'RLS Staging',
          provider_type: 'custom',
          endpoint_url: 'https://example.com/api/v1/infer',
          request_format: 'rls_infer',
          response_json_path: 'data.text',
          litellm_model: '',
        }),
      );
    });

    it('populates custom fields in edit mode', () => {
      const customProvider = makeProvider({
        provider_type: 'custom',
        endpoint_url: 'https://example.com/api/v1/infer',
        request_format: 'rls_infer',
        response_json_path: 'data.text',
      });

      render(
        <ProviderForm
          open={true}
          onOpenChange={vi.fn()}
          provider={customProvider}
        />,
      );

      // Custom fields should be visible and populated
      expect(screen.getByLabelText(/endpoint url/i)).toHaveValue(
        'https://example.com/api/v1/infer',
      );
      expect(screen.getByLabelText(/response json path/i)).toHaveValue('data.text');
    });
  });
});
