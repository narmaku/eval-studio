export interface CreateProviderRequest {
  name: string;
  litellm_model: string;
  api_base?: string | null;
  api_key_env?: string | null;
  proxy?: string | null;
  tags?: string[];
  purpose?: string;
}

export type UpdateProviderRequest = Partial<CreateProviderRequest>;
