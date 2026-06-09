import type { RateLimit } from './evaluation';

export interface CreateProviderRequest {
  name: string;
  default_model?: string;
  api_base?: string | null;
  api_key_env?: string | null;
  proxy?: string | null;
  ssl_cert_path?: string | null;
  ssl_client_key?: string | null;
  tags?: string[];
  default_params?: Record<string, unknown> | null;
  provider_type?: 'litellm' | 'custom';
  endpoint_url?: string | null;
  request_body_template?: string;
  response_json_path?: string;
  rate_limited?: boolean;
  rate_limits?: RateLimit[] | null;
}

export type UpdateProviderRequest = Partial<CreateProviderRequest>;
