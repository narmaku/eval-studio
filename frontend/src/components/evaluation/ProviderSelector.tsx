import { useState, useEffect, useCallback } from 'react';
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
import type { Provider, ProviderModel, ModelEndpoint } from '@/types';

interface ProviderSelectorProps {
  value: ModelEndpoint | undefined;
  onChange: (endpoint: ModelEndpoint) => void;
  disabled?: boolean;
}

export function ProviderSelector({ value, onChange, disabled }: ProviderSelectorProps) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  // selection tracks dropdown value: provider id, 'custom', or '' (nothing selected)
  const [selection, setSelection] = useState<string>(
    value?.provider_id ?? (value?.name ? 'custom' : ''),
  );

  // Model listing state
  const [availableModels, setAvailableModels] = useState<ProviderModel[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState<string>('');

  // Custom fields -- local state, emitted onBlur to avoid infinite re-render
  const [customName, setCustomName] = useState(value?.name ?? '');
  const [customModel, setCustomModel] = useState(value?.default_model ?? '');
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

  const fetchModels = useCallback((providerId: string) => {
    setIsLoadingModels(true);
    setAvailableModels([]);
    setSelectedModelId('');

    api
      .listProviderModels(providerId)
      .then((models) => {
        // Only show the dropdown if we got multiple models or models from a real endpoint
        // (not just the single configured fallback)
        const firstModel = models[0];
        const hasRealModels =
          models.length > 1 ||
          (models.length === 1 && firstModel !== undefined && firstModel.owned_by !== 'configured');
        if (hasRealModels) {
          setAvailableModels(models);
        } else {
          setAvailableModels([]);
        }
      })
      .catch(() => {
        setAvailableModels([]);
      })
      .finally(() => setIsLoadingModels(false));
  }, []);

  const handleProviderSelect = (providerId: string) => {
    setSelection(providerId);
    setAvailableModels([]);
    setSelectedModelId('');

    if (providerId === 'custom') {
      // Don't emit until custom fields are filled
      return;
    }

    const provider = providers.find((p) => p.id === providerId);
    if (provider) {
      onChange({
        provider_id: provider.id,
        name: provider.name,
        default_model: provider.default_model,
        api_base: provider.api_base ?? undefined,
      });

      // Fetch available models for this provider
      fetchModels(provider.id);
    }
  };

  const handleModelSelect = (modelId: string) => {
    setSelectedModelId(modelId);

    const provider = providers.find((p) => p.id === selection);
    if (!provider) return;

    // Build the default_model value: use openai/<model_id> format for OpenAI-compatible endpoints
    const modelValue = provider.api_base ? `openai/${modelId}` : modelId;

    onChange({
      provider_id: provider.id,
      name: provider.name,
      default_model: modelValue,
      api_base: provider.api_base ?? undefined,
    });
  };

  const handleCustomBlur = () => {
    if (customName && customModel) {
      onChange({
        name: customName,
        default_model: customModel,
        api_base: customApiBase || undefined,
      });
    }
  };

  const isCustom = selection === 'custom';
  const showCustomFields = isCustom || error || (!isLoading && providers.length === 0);
  const selectedProvider = providers.find((p) => p.id === selection);
  const showModelDropdown = !isCustom && availableModels.length > 0 && selectedProvider;

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
              value={selection || undefined}
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
                      <span className="text-muted-foreground text-xs">
                        {provider.default_model}
                      </span>
                      {provider.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-[10px] px-1 py-0">
                          {tag}
                        </Badge>
                      ))}
                      {!provider.has_api_key && (
                        <Badge
                          variant="outline"
                          className="text-[10px] px-1 py-0 text-yellow-600 border-yellow-400"
                        >
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

        {/* Model dropdown -- shown when a provider is selected and models are available */}
        {isLoadingModels && (
          <div className="space-y-1.5">
            <Label>Model</Label>
            <div className="text-muted-foreground text-sm py-2">Loading available models...</div>
          </div>
        )}

        {showModelDropdown && (
          <div className="space-y-1.5">
            <Label htmlFor="model-select">Model</Label>
            <Select
              value={selectedModelId || undefined}
              onValueChange={handleModelSelect}
              disabled={disabled}
            >
              <SelectTrigger id="model-select" className="w-full">
                <SelectValue placeholder={`Default: ${selectedProvider.default_model}`} />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{model.id}</span>
                      {model.owned_by && (
                        <span className="text-muted-foreground text-xs">{model.owned_by}</span>
                      )}
                    </span>
                  </SelectItem>
                ))}
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
              <Label htmlFor="custom-model">Default Model</Label>
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
