import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { JudgeReference, Provider, ProviderModel, Rubric } from '@/types';

interface JudgeConfigPanelProps {
  value: JudgeReference | undefined;
  onChange: (config: JudgeReference) => void;
  disabled?: boolean;
}

export function JudgeConfigPanel({ value, onChange, disabled }: JudgeConfigPanelProps) {
  const [judgeProviders, setJudgeProviders] = useState<Provider[]>([]);
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string | undefined>(
    value?.provider_id,
  );
  const [selectedModel, setSelectedModel] = useState<string | undefined>(value?.model);
  const [selectedRubricId, setSelectedRubricId] = useState<string | undefined>(value?.rubric_id);
  const [availableModels, setAvailableModels] = useState<ProviderModel[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  useEffect(() => {
    api
      .listProviders()
      .then(setJudgeProviders)
      .catch(() => {});
    api
      .listRubrics({ page_size: 100 })
      .then((res) => setRubrics(res.items))
      .catch(() => {});
  }, []);

  const fetchModels = (providerId: string, defaultModel: string) => {
    setIsLoadingModels(true);
    api
      .listProviderModels(providerId)
      .then((models) => {
        setAvailableModels(models);
        if (!models.some((m) => m.id === defaultModel) && defaultModel) {
          setAvailableModels([{ id: defaultModel, owned_by: 'configured' }, ...models]);
        }
      })
      .catch(() => {
        setAvailableModels(defaultModel ? [{ id: defaultModel, owned_by: 'configured' }] : []);
      })
      .finally(() => setIsLoadingModels(false));
  };

  const handleProviderSelect = (providerId: string) => {
    const provider = judgeProviders.find((p) => p.id === providerId);
    const model = provider?.default_model ?? '';
    setSelectedProviderId(providerId);
    setSelectedModel(model);
    onChange({ provider_id: providerId, model, rubric_id: selectedRubricId });

    if (provider && !provider.single_model) {
      fetchModels(providerId, provider.default_model);
    } else {
      setAvailableModels(model ? [{ id: model, owned_by: 'configured' }] : []);
    }
  };

  const handleModelSelect = (model: string) => {
    setSelectedModel(model);
    onChange({ provider_id: selectedProviderId, model, rubric_id: selectedRubricId });
  };

  const handleRubricSelect = (rubricId: string) => {
    const newRubricId = rubricId === 'none' ? undefined : rubricId;
    setSelectedRubricId(newRubricId);
    onChange({ provider_id: selectedProviderId, model: selectedModel, rubric_id: newRubricId });
  };

  const effectiveProviderId = value?.provider_id ?? selectedProviderId;
  const effectiveModel = value?.model ?? selectedModel;
  const effectiveRubricId = value?.rubric_id ?? selectedRubricId;
  const selectedProvider = judgeProviders.find((p) => p.id === effectiveProviderId);
  const selectedRubric = rubrics.find((r) => r.id === effectiveRubricId);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Judge Configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {judgeProviders.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {judgeProviders.map((provider) => (
              <button
                key={provider.id}
                type="button"
                disabled={disabled}
                onClick={() => handleProviderSelect(provider.id)}
                className={cn(
                  'rounded-lg border p-3 text-left transition-colors hover:border-primary',
                  effectiveProviderId === provider.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border',
                  disabled && 'pointer-events-none opacity-50',
                )}
              >
                <p className="text-sm font-medium">{provider.name}</p>
                <p className="mt-1 text-xs text-muted-foreground">{provider.default_model}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {provider.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">
                      {tag}
                    </Badge>
                  ))}
                  {!provider.has_api_key && (
                    <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                      no key
                    </Badge>
                  )}
                </div>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No providers configured. Add providers in{' '}
            <code className="text-xs">config/providers.yaml</code> or via Settings.
          </p>
        )}

        {effectiveProviderId && selectedProvider && !selectedProvider.single_model && (
          <div className="space-y-1.5">
            <Label>Model</Label>
            <Select
              value={effectiveModel ?? ''}
              onValueChange={handleModelSelect}
              disabled={disabled || isLoadingModels}
            >
              <SelectTrigger className="w-full">
                <SelectValue
                  placeholder={isLoadingModels ? 'Loading models...' : 'Select a model'}
                />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    {model.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {rubrics.length > 0 && (
          <div className="space-y-1.5">
            <Label>Scoring Rubric (optional)</Label>
            <Select
              value={effectiveRubricId ?? 'none'}
              onValueChange={handleRubricSelect}
              disabled={disabled}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="No rubric — use default scoring" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No rubric — use default scoring</SelectItem>
                {rubrics.map((rubric) => (
                  <SelectItem key={rubric.id} value={rubric.id}>
                    {rubric.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedRubric && (
              <div className="mt-1.5 rounded-md border border-border bg-muted/30 px-3 py-2">
                <p className="text-xs text-muted-foreground">
                  {selectedRubric.dimensions.length} dimension
                  {selectedRubric.dimensions.length !== 1 ? 's' : ''}
                  {' · '}
                  {selectedRubric.aggregation}
                  {' · '}
                  threshold {selectedRubric.pass_threshold}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {selectedRubric.dimensions.map((dim) => (
                    <Badge key={dim.name} variant="outline" className="text-[10px] px-1.5 py-0">
                      {dim.name} (w={dim.weight})
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
