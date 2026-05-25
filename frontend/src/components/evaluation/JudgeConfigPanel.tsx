import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { JudgeReference, Judge } from '@/types';

const PRESETS = [
  {
    key: 'quick_check',
    name: 'Quick Check',
    description: 'Fast single-model evaluation with relaxed thresholds.',
    model: 'gpt-4o-mini',
    threshold: 0.6,
  },
  {
    key: 'standard',
    name: 'Standard',
    description: 'Balanced evaluation with moderate scoring criteria.',
    model: 'gpt-4o',
    threshold: 0.7,
  },
  {
    key: 'rigorous',
    name: 'Rigorous',
    description: 'Thorough multi-judge panel with strict thresholds.',
    model: 'gpt-4o (panel)',
    threshold: 0.8,
  },
] as const;

interface JudgeConfigPanelProps {
  value: JudgeReference | undefined;
  onChange: (config: JudgeReference) => void;
  disabled?: boolean;
}

export function JudgeConfigPanel({ value, onChange, disabled }: JudgeConfigPanelProps) {
  const [selectedPreset, setSelectedPreset] = useState<string | undefined>(value?.preset);
  const [judges, setJudges] = useState<Judge[]>([]);
  const [selectedJudgeId, setSelectedJudgeId] = useState<string | undefined>(value?.judge_id);
  const [advancedLoaded, setAdvancedLoaded] = useState(false);

  // Custom judge fields
  const [customModel, setCustomModel] = useState('');
  const [customTemperature, setCustomTemperature] = useState('0.3');
  const [customThreshold, setCustomThreshold] = useState('0.7');
  const [customPrompt, setCustomPrompt] = useState('');

  const handlePresetSelect = (presetKey: string) => {
    setSelectedPreset(presetKey);
    setSelectedJudgeId(undefined);
    onChange({ preset: presetKey });
  };

  const handleJudgeSelect = (judgeId: string) => {
    setSelectedJudgeId(judgeId);
    setSelectedPreset(undefined);
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
      // Backend may not be available yet -- leave empty list
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
      setSelectedPreset(undefined);
      onChange({ judge_id: judge.id });
    } catch {
      // Error creating judge -- the user can try again
    }
  };

  // Sync from external value -- derive state instead of using an effect.
  // This runs during render (before commit), avoiding the lint error about
  // calling setState inside an effect.
  const effectivePreset = value?.preset ?? selectedPreset;
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
            <div className="grid gap-3 md:grid-cols-3">
              {PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  disabled={disabled}
                  onClick={() => handlePresetSelect(preset.key)}
                  className={cn(
                    'rounded-lg border p-3 text-left transition-colors hover:border-primary',
                    effectivePreset === preset.key
                      ? 'border-primary bg-primary/5'
                      : 'border-border',
                    disabled && 'pointer-events-none opacity-50',
                  )}
                >
                  <p className="text-sm font-medium">{preset.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{preset.description}</p>
                  <div className="mt-2 flex gap-2 text-xs text-muted-foreground">
                    <span>{preset.model}</span>
                    <span>|</span>
                    <span>Threshold: {preset.threshold}</span>
                  </div>
                </button>
              ))}
            </div>
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
                  placeholder="e.g. openai/gpt-4o"
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
