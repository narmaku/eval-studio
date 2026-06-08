import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import type { JudgeReference, Judge, Provider } from '@/types';

interface JudgeConfigPanelProps {
  value: JudgeReference | undefined;
  onChange: (config: JudgeReference) => void;
  disabled?: boolean;
}

export function JudgeConfigPanel({ value, onChange, disabled }: JudgeConfigPanelProps) {
  const [judgeProviders, setJudgeProviders] = useState<Provider[]>([]);
  const [judges, setJudges] = useState<Judge[]>([]);
  const [advancedLoaded, setAdvancedLoaded] = useState(false);
  const [selectedProviderId, setSelectedProviderId] = useState<string | undefined>(
    value?.provider_id,
  );
  const [selectedJudgeId, setSelectedJudgeId] = useState<string | undefined>(value?.judge_id);

  const [customModel, setCustomModel] = useState('');
  const [customTemperature, setCustomTemperature] = useState('0.3');
  const [customThreshold, setCustomThreshold] = useState('0.7');
  const [customPrompt, setCustomPrompt] = useState('');

  useEffect(() => {
    api
      .listProviders('judge')
      .then(setJudgeProviders)
      .catch(() => {});
  }, []);

  const handleProviderSelect = (providerId: string) => {
    setSelectedProviderId(providerId);
    setSelectedJudgeId(undefined);
    onChange({ provider_id: providerId });
  };

  const handleJudgeSelect = (judgeId: string) => {
    setSelectedJudgeId(judgeId);
    setSelectedProviderId(undefined);
    onChange({ judge_id: judgeId });
  };

  const handleTabChange = (tab: string) => {
    if (tab === 'advanced' && !advancedLoaded) {
      setAdvancedLoaded(true);
      void loadJudges();
    }
  };

  const loadJudges = async () => {
    try {
      const result = await api.listJudges();
      setJudges(result);
    } catch {
      // Backend may not be available yet
    }
  };

  const handleCreateCustomJudge = async () => {
    if (!customModel) return;
    try {
      const judge = await api.createJudge({
        name: `Custom: ${customModel}`,
        panel: [
          {
            model: customModel,
            temperature: parseFloat(customTemperature) || 0.3,
            weight: 1,
          },
        ],
        aggregation: 'average',
        prompt_template: customPrompt || '',
        pass_threshold: parseFloat(customThreshold) || 0.7,
        dimensions: [{ name: 'overall', weight: 1 }],
      });
      setSelectedJudgeId(judge.id);
      setSelectedProviderId(undefined);
      onChange({ judge_id: judge.id });
    } catch {
      // Error creating judge
    }
  };

  const effectiveProviderId = value?.provider_id ?? selectedProviderId;
  const effectiveJudgeId = value?.judge_id ?? selectedJudgeId;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Judge Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="simple" onValueChange={handleTabChange}>
          <TabsList>
            <TabsTrigger value="simple">Simple</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          <TabsContent value="simple" className="mt-4">
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
                    <p className="mt-1 text-xs text-muted-foreground">{provider.litellm_model}</p>
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
                <code className="text-xs">config/providers.yaml</code> or via Settings, or use the
                Advanced tab.
              </p>
            )}
          </TabsContent>

          <TabsContent value="advanced" className="mt-4 space-y-4">
            {judges.length > 0 && (
              <div className="space-y-1.5">
                <Label>Existing Judge</Label>
                <Select
                  value={effectiveJudgeId}
                  onValueChange={handleJudgeSelect}
                  disabled={disabled}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select an existing judge..." />
                  </SelectTrigger>
                  <SelectContent>
                    {judges.map((judge) => (
                      <SelectItem key={judge.id} value={judge.id}>
                        {judge.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-3 rounded-lg border p-3">
              <p className="text-sm font-medium">Or create a custom judge</p>

              <div className="space-y-1.5">
                <Label htmlFor="judge-model">Model</Label>
                <Input
                  id="judge-model"
                  placeholder="e.g. gemini/gemini-2.5-flash"
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  disabled={disabled}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="judge-temperature">Temperature</Label>
                  <Input
                    id="judge-temperature"
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={customTemperature}
                    onChange={(e) => setCustomTemperature(e.target.value)}
                    disabled={disabled}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="judge-threshold">Pass Threshold</Label>
                  <Input
                    id="judge-threshold"
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={customThreshold}
                    onChange={(e) => setCustomThreshold(e.target.value)}
                    disabled={disabled}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="judge-prompt">Prompt Template (optional)</Label>
                <Textarea
                  id="judge-prompt"
                  placeholder="Leave empty to use the default judge prompt template..."
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  disabled={disabled}
                  rows={3}
                />
              </div>

              <button
                type="button"
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                disabled={disabled || !customModel}
                onClick={() => void handleCreateCustomJudge()}
              >
                Create & Use
              </button>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
