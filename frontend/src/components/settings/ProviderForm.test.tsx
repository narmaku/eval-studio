import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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

/** A minimal JSON Schema response matching ProviderCreate's schema output. */
const mockSchemaResponse = {
  properties: {
    name: { description: 'A descriptive name for this provider.' },
    default_model: { description: 'The default LLM model identifier.' },
    api_base: { description: 'Base URL for the LLM API endpoint.' },
    api_key_env: { description: 'Name of the environment variable containing the API key.' },
    proxy: { description: 'HTTP proxy URL for routing requests.' },
    ssl_cert_path: { description: 'Path to the SSL client certificate file.' },
    tags: { description: 'Tags for organizing and filtering providers.' },
    purpose: { description: "Provider purpose: 'test' or 'judge'." },
    provider_type: { description: "Provider type: 'litellm' or 'custom'." },
    endpoint_url: { description: 'Full URL for custom provider endpoints.' },
    request_body_template: { description: 'Request body format for custom providers.' },
    response_json_path: { description: 'Dot-path to extract response text.' },
  },
};

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
  request_body_template: 'openai',
  response_json_path: 'choices.0.message.content',
  ...overrides,
});

describe('ProviderForm', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === 'string' ? url : url instanceof URL ? url.href : url.url;
      if (urlStr.includes('/api/v1/providers/schema')) {
        return Promise.resolve(new Response(JSON.stringify(mockSchemaResponse), { status: 200 }));
      }
      return Promise.resolve(new Response('{}', { status: 404 }));
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
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

  it('renders tooltip icons after schema is fetched', async () => {
    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

    // Tooltips appear asynchronously after schema fetch resolves
    await waitFor(() => {
      const infoButtons = screen.getAllByRole('button', { name: /field info/i });
      // Expect tooltips for the visible litellm fields:
      // provider_type, name, default_model, api_base, api_key_env, proxy, ssl_cert_path, purpose, tags
      expect(infoButtons.length).toBeGreaterThanOrEqual(9);
    });
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

  it('allows empty model for litellm type (optional field)', async () => {
    const user = userEvent.setup();
    mockCreateProvider.mockResolvedValue(makeProvider({ default_model: '' }));

    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByLabelText(/name/i), 'My Provider');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockCreateProvider).toHaveBeenCalledTimes(1);
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
      expect(screen.queryByLabelText(/request body template/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/response json path/i)).not.toBeInTheDocument();

      // Select "Custom API" type
      await user.click(screen.getByLabelText(/provider type/i));
      await user.click(screen.getByText('Custom API'));

      // Custom fields should be visible
      expect(screen.getByLabelText(/endpoint url/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/request body template/i)).toBeInTheDocument();
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
      await user.type(screen.getByLabelText(/endpoint url/i), 'https://example.com/api/v1/infer');

      // Set request body template via paste (type() interprets braces as keyboard modifiers)
      const templateInput = screen.getByLabelText(/request body template/i);
      await user.click(templateInput);
      await user.paste('{"question": "{{message}}"}');

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
          request_body_template: '{"question": "{{message}}"}',
          response_json_path: 'data.text',
        }),
      );
    });

    it('populates custom fields in edit mode', () => {
      const customProvider = makeProvider({
        provider_type: 'custom',
        endpoint_url: 'https://example.com/api/v1/infer',
        request_body_template: '{"question": "{{message}}"}',
        response_json_path: 'data.text',
      });

      render(<ProviderForm open={true} onOpenChange={vi.fn()} provider={customProvider} />);

      // Custom fields should be visible and populated
      expect(screen.getByLabelText(/endpoint url/i)).toHaveValue(
        'https://example.com/api/v1/infer',
      );
      expect(screen.getByLabelText(/response json path/i)).toHaveValue('data.text');
    });
  });
});
