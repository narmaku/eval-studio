import { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FieldTooltip } from '@/components/ui/FieldTooltip';
import { LLMParamsPanel } from '@/components/evaluation/LLMParamsPanel';
import { Plus, Trash2 } from 'lucide-react';
import { useProviderStore } from '@/stores/providerStore';
import { api } from '@/services/api';
import type { Provider, CreateProviderRequest, LLMParams, RateLimit } from '@/types';

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
  const [sslClientKey, setSslClientKey] = useState(provider?.ssl_client_key ?? '');
  const [tagsInput, setTagsInput] = useState(provider?.tags?.join(', ') ?? '');
  const [defaultParams, setDefaultParams] = useState<LLMParams>(
    (provider?.default_params as LLMParams) ?? {},
  );

  // Single-model provider
  const [singleModel, setSingleModel] = useState(provider?.single_model ?? false);

  // Rate limit fields
  const [rateLimited, setRateLimited] = useState(provider?.rate_limited ?? false);
  const [rateLimits, setRateLimits] = useState<RateLimit[]>(provider?.rate_limits ?? []);

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
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const isCustom = providerType === 'custom';

  const handleRateLimitedChange = (checked: boolean | 'indeterminate') => {
    const isChecked = checked === true;
    setRateLimited(isChecked);
    if (isChecked && rateLimits.length === 0) {
      setRateLimits([{ value: 10, unit: 'requests', per: 'minute' }]);
    }
  };

  const addRateLimit = () => {
    setRateLimits([...rateLimits, { value: 10, unit: 'requests', per: 'minute' }]);
  };

  const removeRateLimit = (index: number) => {
    setRateLimits(rateLimits.filter((_, i) => i !== index));
  };

  const updateRateLimit = (index: number, field: keyof RateLimit, value: unknown) => {
    setRateLimits(rateLimits.map((rl, i) => (i === index ? { ...rl, [field]: value } : rl)));
  };

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

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const data: CreateProviderRequest = {
        name: name.trim() || 'test',
        default_model: isCustom ? '' : defaultModel.trim(),
        api_base: apiBase.trim() || null,
        api_key_env: apiKeyEnv.trim() || null,
        proxy: proxy.trim() || null,
        ssl_cert_path: sslCertPath.trim() || null,
        ssl_client_key: sslClientKey.trim() || null,
        tags: [],
        provider_type: providerType,
        endpoint_url: isCustom ? endpointUrl.trim() || null : null,
        request_body_template: isCustom ? requestBodyTemplate.trim() || undefined : undefined,
        response_json_path: isCustom ? responseJsonPath.trim() : 'choices.0.message.content',
      };
      const result = await api.testProviderConnection(data);
      setTestResult(result);
    } catch {
      setTestResult({ success: false, message: 'Failed to reach the server' });
    } finally {
      setIsTesting(false);
    }
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
        default_model: isCustom || singleModel ? '' : defaultModel.trim(),
        api_base: apiBase.trim() || null,
        api_key_env: apiKeyEnv.trim() || null,
        proxy: proxy.trim() || null,
        ssl_cert_path: sslCertPath.trim() || null,
        ssl_client_key: sslClientKey.trim() || null,
        tags,
        default_params:
          Object.keys(defaultParams).length > 0 ? (defaultParams as Record<string, unknown>) : null,
        provider_type: providerType,
        endpoint_url: isCustom ? endpointUrl.trim() || null : null,
        request_body_template: isCustom ? requestBodyTemplate.trim() || undefined : undefined,
        response_json_path: isCustom ? responseJsonPath.trim() : 'choices.0.message.content',
        single_model: singleModel,
        rate_limited: rateLimited,
        rate_limits: rateLimited && rateLimits.length > 0 ? rateLimits : null,
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
        <div className="flex items-center gap-2">
          <Checkbox
            id="single-model"
            checked={singleModel}
            onCheckedChange={(checked) => setSingleModel(checked === true)}
          />
          <Label htmlFor="single-model" className="text-sm font-normal cursor-pointer">
            Single-model provider
          </Label>
          {fieldDescriptions.single_model && (
            <FieldTooltip description={fieldDescriptions.single_model} />
          )}
        </div>
      )}

      {!isCustom && !singleModel && (
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
          <Label htmlFor="provider-ssl-cert">SSL Client Certificate (optional)</Label>
          {fieldDescriptions.ssl_cert_path && (
            <FieldTooltip description={fieldDescriptions.ssl_cert_path} />
          )}
        </div>
        <Input
          id="provider-ssl-cert"
          value={sslCertPath}
          onChange={(e) => setSslCertPath(e.target.value)}
          placeholder="e.g., /path/to/cert.pem"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label htmlFor="provider-ssl-key">SSL Client Key (optional)</Label>
          {fieldDescriptions.ssl_client_key && (
            <FieldTooltip description={fieldDescriptions.ssl_client_key} />
          )}
        </div>
        <Input
          id="provider-ssl-key"
          value={sslClientKey}
          onChange={(e) => setSslClientKey(e.target.value)}
          placeholder="e.g., /path/to/key.pem"
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Checkbox
            id="provider-rate-limited"
            checked={rateLimited}
            onCheckedChange={handleRateLimitedChange}
          />
          <Label htmlFor="provider-rate-limited" className="cursor-pointer">
            This provider is rate-limited
          </Label>
        </div>

        {rateLimited && (
          <div className="space-y-2 pl-6">
            {rateLimits.map((rl, index) => (
              <div key={index} className="flex items-center gap-2">
                <Input
                  type="number"
                  min={1}
                  value={rl.value}
                  onChange={(e) => updateRateLimit(index, 'value', parseInt(e.target.value) || 1)}
                  className="w-20"
                  aria-label={`Rate limit value ${index + 1}`}
                />
                <Select
                  value={rl.unit}
                  onValueChange={(v) => updateRateLimit(index, 'unit', v)}
                >
                  <SelectTrigger className="w-28" aria-label={`Rate limit unit ${index + 1}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="requests">requests</SelectItem>
                    <SelectItem value="tokens">tokens</SelectItem>
                  </SelectContent>
                </Select>
                <span className="text-sm text-muted-foreground">/</span>
                <Select
                  value={rl.per}
                  onValueChange={(v) => updateRateLimit(index, 'per', v)}
                >
                  <SelectTrigger className="w-28" aria-label={`Rate limit per ${index + 1}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="second">second</SelectItem>
                    <SelectItem value="minute">minute</SelectItem>
                    <SelectItem value="hour">hour</SelectItem>
                    <SelectItem value="day">day</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0"
                  onClick={() => removeRateLimit(index)}
                  aria-label={`Remove rate limit ${index + 1}`}
                  type="button"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={addRateLimit}
              type="button"
            >
              <Plus className="mr-1 h-3 w-3" />
              Add Limit
            </Button>
          </div>
        )}
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

      {testResult && (
        <div
          className={`rounded-md p-3 text-sm ${testResult.success ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-destructive/10 text-destructive'}`}
        >
          <p>
            {testResult.success ? '✓' : '✗'} {testResult.message}
          </p>
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <Button
          variant="outline"
          onClick={handleTest}
          disabled={isTesting || isSaving}
          className="flex-1"
          type="button"
        >
          {isTesting ? 'Testing...' : 'Test Connection'}
        </Button>
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
