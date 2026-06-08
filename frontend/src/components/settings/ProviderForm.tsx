import { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FieldTooltip } from '@/components/ui/FieldTooltip';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import { useProviderStore } from '@/stores/providerStore';
import type { Provider, CreateProviderRequest, LLMParams } from '@/types';

interface ProviderFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider?: Provider;
  onSaved?: () => void;
}

/**
 * Wrapper component that controls Sheet open/close.
 * Uses a key to remount the inner form each time the sheet opens,
 * ensuring a clean state reset without useEffect or ref access during render.
 */
export function ProviderForm({ open, onOpenChange, provider, onSaved }: ProviderFormProps) {
  const [formKey, setFormKey] = useState(0);

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setFormKey((k) => k + 1);
    }
    onOpenChange(nextOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{provider ? 'Edit Provider' : 'New Provider'}</SheetTitle>
        </SheetHeader>
        {open && (
          <ProviderFormInner
            key={formKey}
            provider={provider}
            onSaved={onSaved}
            onClose={() => onOpenChange(false)}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}

interface ProviderFormInnerProps {
  provider?: Provider;
  onSaved?: () => void;
  onClose: () => void;
}

/** Map of field name -> description, extracted from JSON Schema. */
type FieldDescriptions = Record<string, string>;

function ProviderFormInner({ provider, onSaved, onClose }: ProviderFormInnerProps) {
  const createProvider = useProviderStore((s) => s.createProvider);
  const updateProvider = useProviderStore((s) => s.updateProvider);

  const [fieldDescriptions, setFieldDescriptions] = useState<FieldDescriptions>({});

  useEffect(() => {
    let cancelled = false;
    fetch('/api/v1/providers/schema')
      .then((res) => (res.ok ? res.json() : null))
      .then((schema: Record<string, unknown> | null) => {
        if (cancelled || !schema) return;
        const props = schema.properties as Record<string, { description?: string }> | undefined;
        if (!props) return;
        const descs: FieldDescriptions = {};
        for (const [key, value] of Object.entries(props)) {
          if (value.description) {
            descs[key] = value.description;
          }
        }
        setFieldDescriptions(descs);
      })
      .catch(() => {
        /* schema fetch is best-effort; tooltips simply won't appear */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const isEditMode = !!provider;

  const [providerType, setProviderType] = useState<'litellm' | 'custom'>(
    (provider?.provider_type as 'litellm' | 'custom') ?? 'litellm',
  );
  const [name, setName] = useState(provider?.name ?? '');
  const [defaultModel, setDefaultModel] = useState(provider?.default_model ?? '');
  const [apiBase, setApiBase] = useState(provider?.api_base ?? '');
  const [apiKeyEnv, setApiKeyEnv] = useState('');
  const [proxy, setProxy] = useState(provider?.proxy ?? '');
  const [sslCertPath, setSslCertPath] = useState(provider?.ssl_cert_path ?? '');
  const [tagsInput, setTagsInput] = useState(provider?.tags?.join(', ') ?? '');
  const [defaultParams, setDefaultParams] = useState<LLMParams>(
    (provider?.default_params as LLMParams) ?? {},
  );

  // Custom provider fields
  const [endpointUrl, setEndpointUrl] = useState(provider?.endpoint_url ?? '');
  const [requestBodyTemplate, setRequestBodyTemplate] = useState(
    provider?.request_body_template ?? '',
  );
  const [responseJsonPath, setResponseJsonPath] = useState(
    provider?.response_json_path ?? 'choices.0.message.content',
  );

  const [errors, setErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  const isCustom = providerType === 'custom';

  const validate = (): boolean => {
    const newErrors: string[] = [];
    if (!name.trim()) {
      newErrors.push('Name is required');
    }
    if (isCustom && !endpointUrl.trim()) {
      newErrors.push('Endpoint URL is required');
    }
    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    setIsSaving(true);
    try {
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      const data: CreateProviderRequest = {
        name: name.trim(),
        default_model: isCustom ? '' : defaultModel.trim(),
        api_base: apiBase.trim() || null,
        api_key_env: apiKeyEnv.trim() || null,
        proxy: proxy.trim() || null,
        ssl_cert_path: sslCertPath.trim() || null,
        tags,
        default_params:
          Object.keys(defaultParams).length > 0 ? (defaultParams as Record<string, unknown>) : null,
        provider_type: providerType,
        endpoint_url: isCustom ? endpointUrl.trim() || null : null,
        request_body_template: isCustom ? requestBodyTemplate.trim() || null : null,
        response_json_path: isCustom ? responseJsonPath.trim() : 'choices.0.message.content',
      };

      if (isEditMode && provider) {
        await updateProvider(provider.id, data);
      } else {
        await createProvider(data);
      }

      onSaved?.();
      onClose();
    } catch {
      setErrors(['Failed to save provider. Please try again.']);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 px-4 pb-4">
      {errors.length > 0 && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {errors.map((e, i) => (
            <p key={i}>{e}</p>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="provider-type">Provider Type</Label>
          {fieldDescriptions.provider_type && (
            <FieldTooltip description={fieldDescriptions.provider_type} />
          )}
        </div>
        <Select
          value={providerType}
          onValueChange={(v) => setProviderType(v as 'litellm' | 'custom')}
        >
          <SelectTrigger className="w-full" id="provider-type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="litellm">LiteLLM (OpenAI-compatible)</SelectItem>
            <SelectItem value="custom">Custom API</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="provider-name">Name</Label>
          {fieldDescriptions.name && <FieldTooltip description={fieldDescriptions.name} />}
        </div>
        <Input
          id="provider-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., My Local LLM"
        />
      </div>

      {!isCustom && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="provider-model">Default Model</Label>
            {fieldDescriptions.default_model && (
              <FieldTooltip description={fieldDescriptions.default_model} />
            )}
          </div>
          <Input
            id="provider-model"
            value={defaultModel}
            onChange={(e) => setDefaultModel(e.target.value)}
            placeholder="e.g., openai/gpt-4 or ollama/llama3"
          />
        </div>
      )}

      {isCustom && (
        <>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="provider-endpoint-url">Endpoint URL</Label>
              {fieldDescriptions.endpoint_url && (
                <FieldTooltip description={fieldDescriptions.endpoint_url} />
              )}
            </div>
            <Input
              id="provider-endpoint-url"
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              placeholder="e.g., https://host/api/v1/inference"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="provider-request-template">Request Body Template</Label>
              {fieldDescriptions.request_body_template && (
                <FieldTooltip description={fieldDescriptions.request_body_template} />
              )}
            </div>
            <Textarea
              id="provider-request-template"
              value={requestBodyTemplate}
              onChange={(e) => setRequestBodyTemplate(e.target.value)}
              placeholder={'{"question": "{{message}}"}'}
              rows={3}
              className="font-mono text-xs"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="provider-response-path">Response JSON Path</Label>
              {fieldDescriptions.response_json_path && (
                <FieldTooltip description={fieldDescriptions.response_json_path} />
              )}
            </div>
            <Input
              id="provider-response-path"
              value={responseJsonPath}
              onChange={(e) => setResponseJsonPath(e.target.value)}
              placeholder="e.g., data.text"
            />
          </div>
        </>
      )}

      {!isCustom && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="provider-api-base">API Base (optional)</Label>
            {fieldDescriptions.api_base && (
              <FieldTooltip description={fieldDescriptions.api_base} />
            )}
          </div>
          <Input
            id="provider-api-base"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            placeholder="e.g., http://localhost:11434/v1"
          />
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="provider-api-key-env">API Key Env Var (optional)</Label>
          {fieldDescriptions.api_key_env && (
            <FieldTooltip description={fieldDescriptions.api_key_env} />
          )}
        </div>
        <Input
          id="provider-api-key-env"
          value={apiKeyEnv}
          onChange={(e) => setApiKeyEnv(e.target.value)}
          placeholder="e.g., OPENAI_API_KEY"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="provider-proxy">Proxy (optional)</Label>
          {fieldDescriptions.proxy && <FieldTooltip description={fieldDescriptions.proxy} />}
        </div>
        <Input
          id="provider-proxy"
          value={proxy}
          onChange={(e) => setProxy(e.target.value)}
          placeholder="e.g., http://proxy:3128"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="provider-ssl-cert">SSL Certificate Bundle (optional)</Label>
          {fieldDescriptions.ssl_cert_path && (
            <FieldTooltip description={fieldDescriptions.ssl_cert_path} />
          )}
        </div>
        <Input
          id="provider-ssl-cert"
          value={sslCertPath}
          onChange={(e) => setSslCertPath(e.target.value)}
          placeholder="e.g., /etc/pki/tls/certs/ca-bundle.crt"
        />
      </div>

      {!isCustom && (
        <LLMParamsPanel
          label="Default LLM Parameters"
          value={defaultParams}
          onChange={setDefaultParams}
        />
      )}

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="provider-tags">Tags (optional, comma-separated)</Label>
          {fieldDescriptions.tags && <FieldTooltip description={fieldDescriptions.tags} />}
        </div>
        <Input
          id="provider-tags"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="e.g., local, fast, gpu"
        />
      </div>

      <div className="flex gap-2 pt-2">
        <Button onClick={handleSave} disabled={isSaving} className="flex-1">
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
        <Button variant="outline" onClick={onClose} className="flex-1">
          Cancel
        </Button>
      </div>
    </div>
  );
}
