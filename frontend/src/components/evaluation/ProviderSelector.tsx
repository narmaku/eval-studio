import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { api } from '@/services/api';
import type { Provider, ModelEndpoint } from '@/types';

interface ProviderSelectorProps {
  value: ModelEndpoint | undefined;
  onChange: (endpoint: ModelEndpoint) => void;
  disabled?: boolean;
}

export function ProviderSelector({ value, onChange, disabled }: ProviderSelectorProps) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedId, setSelectedId] = useState<string>(value?.provider_id ?? '');
  const [isCustom, setIsCustom] = useState(!value?.provider_id);

  // Custom fields -- local state, emitted onBlur to avoid infinite re-render
  const [customName, setCustomName] = useState(value?.name ?? '');
  const [customModel, setCustomModel] = useState(value?.litellm_model ?? '');
  const [customApiBase, setCustomApiBase] = useState(value?.api_base ?? '');

  useEffect(() => {
    api
      .listProviders('test')
      .then((data) => {
        setProviders(data);
        setError(false);
      })
      .catch(() => {
        setError(true);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const handleProviderSelect = (providerId: string) => {
    if (providerId === 'custom') {
      setIsCustom(true);
      setSelectedId('');
      return;
    }

    setIsCustom(false);
    setSelectedId(providerId);
    const provider = providers.find((p) => p.id === providerId);
    if (provider) {
      onChange({
        provider_id: provider.id,
        name: provider.name,
        litellm_model: provider.litellm_model,
        api_base: provider.api_base ?? undefined,
      });
    }
  };

  const handleCustomBlur = () => {
    if (customName && customModel) {
      onChange({
        name: customName,
        litellm_model: customModel,
        api_base: customApiBase || undefined,
      });
    }
  };

  const showCustomFields = isCustom || error || providers.length === 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Model / Provider</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Provider dropdown -- only show when providers are available */}
        {!error && (
          <div className="space-y-1.5">
            <Label htmlFor="provider-select">Provider</Label>
            <Select
              value={isCustom ? 'custom' : selectedId}
              onValueChange={handleProviderSelect}
              disabled={disabled || isLoading}
            >
              <SelectTrigger id="provider-select" className="w-full">
                <SelectValue
                  placeholder={isLoading ? 'Loading providers...' : 'Select a provider...'}
                />
              </SelectTrigger>
              <SelectContent>
                {providers.map((provider) => (
                  <SelectItem key={provider.id} value={provider.id}>
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{provider.name}</span>
                      <span className="text-muted-foreground text-xs">{provider.litellm_model}</span>
                      {provider.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-[10px] px-1 py-0">
                          {tag}
                        </Badge>
                      ))}
                      {!provider.has_api_key && (
                        <Badge variant="outline" className="text-[10px] px-1 py-0 text-yellow-600 border-yellow-400">
                          (no key)
                        </Badge>
                      )}
                    </span>
                  </SelectItem>
                ))}
                {providers.length > 0 && <SelectSeparator />}
                <SelectItem value="custom">Custom...</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Custom fields -- shown when "Custom" is selected or API failed */}
        {!isLoading && showCustomFields && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="custom-name">Name</Label>
              <Input
                id="custom-name"
                placeholder="e.g. GPT-4o"
                disabled={disabled}
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                onBlur={handleCustomBlur}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="custom-model">LiteLLM Model</Label>
              <Input
                id="custom-model"
                placeholder="e.g. openai/gpt-4o"
                disabled={disabled}
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                onBlur={handleCustomBlur}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="custom-api-base">API Base URL (optional)</Label>
              <Input
                id="custom-api-base"
                placeholder="e.g. https://api.openai.com/v1"
                disabled={disabled}
                value={customApiBase}
                onChange={(e) => setCustomApiBase(e.target.value)}
                onBlur={handleCustomBlur}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
