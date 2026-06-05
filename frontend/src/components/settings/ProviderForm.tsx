import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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

function ProviderFormInner({ provider, onSaved, onClose }: ProviderFormInnerProps) {
  const createProvider = useProviderStore((s) => s.createProvider);
  const updateProvider = useProviderStore((s) => s.updateProvider);

  const isEditMode = !!provider;

  const [name, setName] = useState(provider?.name ?? '');
  const [litellmModel, setLitellmModel] = useState(provider?.litellm_model ?? '');
  const [apiBase, setApiBase] = useState(provider?.api_base ?? '');
  const [apiKeyEnv, setApiKeyEnv] = useState('');
  const [proxy, setProxy] = useState(provider?.proxy ?? '');
  const [sslCertPath, setSslCertPath] = useState(provider?.ssl_cert_path ?? '');
  const [purpose, setPurpose] = useState(provider?.purpose ?? 'test');
  const [tagsInput, setTagsInput] = useState(provider?.tags?.join(', ') ?? '');
  const [defaultParams, setDefaultParams] = useState<LLMParams>(
    (provider?.default_params as LLMParams) ?? {},
  );
  const [errors, setErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  const validate = (): boolean => {
    const newErrors: string[] = [];
    if (!name.trim()) {
      newErrors.push('Name is required');
    }
    if (!litellmModel.trim()) {
      newErrors.push('LiteLLM model is required');
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
        litellm_model: litellmModel.trim(),
        api_base: apiBase.trim() || null,
        api_key_env: apiKeyEnv.trim() || null,
        proxy: proxy.trim() || null,
        ssl_cert_path: sslCertPath.trim() || null,
        tags,
        purpose,
        default_params: Object.keys(defaultParams).length > 0 ? (defaultParams as Record<string, unknown>) : null,
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
        <Label htmlFor="provider-name">Name</Label>
        <Input
          id="provider-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., My Local LLM"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="provider-model">LiteLLM Model</Label>
        <Input
          id="provider-model"
          value={litellmModel}
          onChange={(e) => setLitellmModel(e.target.value)}
          placeholder="e.g., openai/gpt-4 or ollama/llama3"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="provider-api-base">API Base (optional)</Label>
        <Input
          id="provider-api-base"
          value={apiBase}
          onChange={(e) => setApiBase(e.target.value)}
          placeholder="e.g., http://localhost:11434/v1"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="provider-api-key-env">API Key Env Var (optional)</Label>
        <Input
          id="provider-api-key-env"
          value={apiKeyEnv}
          onChange={(e) => setApiKeyEnv(e.target.value)}
          placeholder="e.g., OPENAI_API_KEY"
        />
        <p className="text-xs text-muted-foreground">
          Name of the environment variable containing the API key. No direct key storage.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="provider-proxy">Proxy (optional)</Label>
        <Input
          id="provider-proxy"
          value={proxy}
          onChange={(e) => setProxy(e.target.value)}
          placeholder="e.g., http://proxy:3128"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="provider-ssl-cert">SSL Certificate Bundle (optional)</Label>
        <Input
          id="provider-ssl-cert"
          value={sslCertPath}
          onChange={(e) => setSslCertPath(e.target.value)}
          placeholder="e.g., /etc/pki/tls/certs/ca-bundle.crt"
        />
        <p className="text-xs text-muted-foreground">
          Path to a custom CA certificate bundle for proxy/TLS verification.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="provider-purpose">Purpose</Label>
        <Select value={purpose} onValueChange={setPurpose}>
          <SelectTrigger className="w-full" id="provider-purpose">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="test">Test (model under test)</SelectItem>
            <SelectItem value="judge">Judge (scoring model)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <LLMParamsPanel label="Default LLM Parameters" value={defaultParams} onChange={setDefaultParams} />

      <div className="space-y-2">
        <Label htmlFor="provider-tags">Tags (optional, comma-separated)</Label>
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
