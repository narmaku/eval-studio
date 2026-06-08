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
    provider_type: { description: "Provider type: 'litellm' or 'custom'." },
    endpoint_url: { description: 'Full URL for custom provider endpoints.' },
    request_body_template: { description: 'Request body format for custom providers.' },
    response_json_path: { description: 'Dot-path to extract response text.' },
  },
};

const makeProvider = (overrides: Partial<Provider> = {}): Provider => ({
  id: 'p-1',
  name: 'Existing Provider',
  default_model: 'openai/gpt-4',
  api_base: 'https://api.example.com',
  has_api_key: true,
  proxy: null,
  ssl_cert_path: null,
  tags: ['fast'],
  default_params: null,
  provider_type: 'litellm',
  endpoint_url: null,
  request_body_template: 'openai',
  response_json_path: 'choices.0.message.content',
  ...overrides,
});

describe('ProviderForm', () => {
  const originalFetch = globalThis.fetch;

  let testConnectionResponse: { success: boolean; message: string; details?: string } | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
    testConnectionResponse = null;
    globalThis.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === 'string' ? url : url instanceof URL ? url.href : url.url;
      if (urlStr.includes('/api/v1/providers/schema')) {
        return Promise.resolve(new Response(JSON.stringify(mockSchemaResponse), { status: 200 }));
      }
      if (urlStr.includes('/api/v1/providers/test') && testConnectionResponse) {
        return Promise.resolve(
          new Response(JSON.stringify(testConnectionResponse), { status: 200 }),
        );
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
    expect(screen.getByLabelText(/default model/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api base/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api key env/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/proxy/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tags/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/provider type/i)).toBeInTheDocument();
  });

  it('renders tooltip icons after schema is fetched', async () => {
    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

    // Tooltips appear asynchronously after schema fetch resolves
    await waitFor(() => {
      const infoButtons = screen.getAllByRole('button', { name: /field info/i });
      // Expect tooltips for the visible litellm fields:
      // provider_type, name, default_model, api_base, api_key_env, proxy, ssl_cert_path, tags
      expect(infoButtons.length).toBeGreaterThanOrEqual(8);
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
    expect(screen.getByLabelText(/default model/i)).toHaveValue('openai/gpt-4');
    expect(screen.getByLabelText(/api base/i)).toHaveValue('https://api.example.com');
  });

  it('validates: rejects empty name', async () => {
    const user = userEvent.setup();
    render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

    // Fill in model but not name
    await user.type(screen.getByLabelText(/default model/i), 'openai/gpt-4');
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
    await user.type(screen.getByLabelText(/default model/i), 'openai/gpt-4');

    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(mockCreateProvider).toHaveBeenCalledTimes(1);
    expect(mockCreateProvider).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'New Provider',
        default_model: 'openai/gpt-4',
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
    it('hides Default Model field when custom type is selected', async () => {
      const user = userEvent.setup();
      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      // Initially Default Model should be visible
      expect(screen.getByLabelText(/default model/i)).toBeInTheDocument();

      // Select "Custom API" type
      await user.click(screen.getByLabelText(/provider type/i));
      await user.click(screen.getByText('Custom API'));

      // Default Model should be hidden
      expect(screen.queryByLabelText(/default model/i)).not.toBeInTheDocument();
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

  describe('test connection', () => {
    it('renders test connection button', () => {
      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);
      expect(screen.getByRole('button', { name: /test connection/i })).toBeInTheDocument();
    });

    it('shows success message on successful test', async () => {
      const user = userEvent.setup();
      testConnectionResponse = { success: true, message: 'Connected successfully' };

      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      await user.click(screen.getByRole('button', { name: /test connection/i }));

      await waitFor(() => {
        expect(screen.getByText(/Connected successfully/)).toBeInTheDocument();
      });

      // Verify green styling (success container)
      const resultDiv = screen.getByText(/Connected successfully/).closest('div');
      expect(resultDiv?.className).toMatch(/bg-green/);
    });

    it('shows error message on failed test', async () => {
      const user = userEvent.setup();
      testConnectionResponse = { success: false, message: 'Connection failed: refused' };

      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      await user.click(screen.getByRole('button', { name: /test connection/i }));

      await waitFor(() => {
        expect(screen.getByText(/Connection failed: refused/)).toBeInTheDocument();
      });

      // Verify destructive styling (error container)
      const resultDiv = screen.getByText(/Connection failed: refused/).closest('div');
      expect(resultDiv?.className).toMatch(/destructive/);
    });

    it('shows loading state during test', async () => {
      const user = userEvent.setup();
      // Use a promise that we control to hold the fetch in progress
      let resolveFetch: (value: Response) => void;
      const pendingFetch = new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      });

      globalThis.fetch = vi.fn((url: string | URL | Request) => {
        const urlStr = typeof url === 'string' ? url : url instanceof URL ? url.href : url.url;
        if (urlStr.includes('/api/v1/providers/schema')) {
          return Promise.resolve(new Response(JSON.stringify(mockSchemaResponse), { status: 200 }));
        }
        if (urlStr.includes('/api/v1/providers/test')) {
          return pendingFetch;
        }
        return Promise.resolve(new Response('{}', { status: 404 }));
      }) as unknown as typeof fetch;

      render(<ProviderForm open={true} onOpenChange={vi.fn()} />);

      await user.click(screen.getByRole('button', { name: /test connection/i }));

      // Should show loading text
      expect(screen.getByText('Testing...')).toBeInTheDocument();

      // Resolve the fetch to clean up
      resolveFetch!(
        new Response(JSON.stringify({ success: true, message: 'Connected' }), { status: 200 }),
      );

      await waitFor(() => {
        expect(screen.getByText(/Test Connection/)).toBeInTheDocument();
      });
    });
  });
});
