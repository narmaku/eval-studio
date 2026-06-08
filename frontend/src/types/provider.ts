export interface CreateProviderRequest {
  name: string;
  litellm_model?: string;
  api_base?: string | null;
  api_key_env?: string | null;
  proxy?: string | null;
  ssl_cert_path?: string | null;
  tags?: string[];
  default_params?: Record<string, unknown> | null;
  provider_type?: 'litellm' | 'custom';
  endpoint_url?: string | null;
  request_body_template?: string;
  response_json_path?: string;
}

export type UpdateProviderRequest = Partial<CreateProviderRequest>;
