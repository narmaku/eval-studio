import { useState, useCallback } from 'react';
import { ChevronLeft, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useRubricStore } from '@/stores/rubricStore';
import type { DetectedMetric } from '@/types';

const STEP_LABELS = ['Import Rubric', 'Preview & Confirm'] as const;

const FORMAT_LABELS: Record<string, string> = {
  rubric_kit: 'rubric-kit',
  geval: 'geval',
  ls_eval_system_config: 'ls-eval system config',
  simple: 'simple',
  unknown: 'unknown',
};

interface RubricImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported?: () => void;
}

export function RubricImportDialog({ open, onOpenChange, onImported }: RubricImportDialogProps) {
  const importRubric = useRubricStore((s) => s.importRubric);
  const analyzeRubric = useRubricStore((s) => s.analyzeRubric);
  const analyzeResult = useRubricStore((s) => s.analyzeResult);
  const isAnalyzing = useRubricStore((s) => s.isAnalyzing);
  const clearAnalysis = useRubricStore((s) => s.clearAnalysis);

  const [step, setStep] = useState<1 | 2>(1);
  const [yamlContent, setYamlContent] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 2 form state
  const [selectedMetricIndex, setSelectedMetricIndex] = useState(0);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');

  const selectedMetric: DetectedMetric | undefined = analyzeResult?.metrics[selectedMetricIndex];

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result;
      if (typeof text === 'string') {
        setYamlContent(text);
        setError(null);
      }
    };
    reader.readAsText(file);
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!yamlContent.trim()) return;
    setError(null);
    try {
      await analyzeRubric(yamlContent);
      // Pre-fill from first metric after analysis succeeds
      const result = useRubricStore.getState().analyzeResult;
      if (result && result.metrics.length > 0) {
        const firstMetric = result.metrics[0];
        if (firstMetric) {
          setName(firstMetric.suggested_name);
          setDescription(firstMetric.suggested_description ?? '');
        }
        setSelectedMetricIndex(0);
      }
      setStep(2);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed';
      setError(message);
    }
  }, [yamlContent, analyzeRubric]);

  const handleMetricChange = useCallback(
    (value: string) => {
      const idx = parseInt(value, 10);
      setSelectedMetricIndex(idx);
      const metric = analyzeResult?.metrics[idx];
      if (metric) {
        setName(metric.suggested_name);
        setDescription(metric.suggested_description ?? '');
      }
    },
    [analyzeResult],
  );

  const handleImport = useCallback(async () => {
    if (!yamlContent.trim() || !name.trim()) return;
    setIsImporting(true);
    setError(null);
    try {
      const parsedTags = tags
        ? tags
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean)
        : undefined;

      await importRubric({
        yaml_content: yamlContent,
        name: name,
        description: description || undefined,
        tags: parsedTags,
        metric_id: selectedMetric?.metric_id ?? undefined,
      });
      onImported?.();
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Import failed';
      setError(message);
    } finally {
      setIsImporting(false);
    }
  }, [
    yamlContent,
    name,
    description,
    tags,
    selectedMetric,
    importRubric,
    onImported,
    onOpenChange,
  ]);

  const resetState = useCallback(() => {
    setStep(1);
    setYamlContent('');
    setError(null);
    setIsImporting(false);
    setSelectedMetricIndex(0);
    setName('');
    setDescription('');
    setTags('');
    clearAnalysis();
  }, [clearAnalysis]);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        resetState();
      }
      onOpenChange(nextOpen);
    },
    [resetState, onOpenChange],
  );

  const handleBack = useCallback(() => {
    setStep(1);
    setError(null);
  }, []);

  const stepIndicator = (
    <div
      className="flex items-center justify-center gap-2 mb-4"
      data-testid="step-indicator"
      role="group"
      aria-label={`Step ${step} of 2: ${STEP_LABELS[step - 1]}`}
    >
      {[1, 2].map((s) => (
        <div
          key={s}
          role="presentation"
          aria-hidden="true"
          className={`h-2 w-2 rounded-full ${s === step ? 'bg-primary' : 'bg-muted'}`}
        />
      ))}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {step === 1 && 'Import Rubric'}
            {step === 2 && 'Preview & Confirm'}
          </DialogTitle>
          <DialogDescription>
            {step === 1 && 'Upload a YAML file or paste content to auto-detect format.'}
            {step === 2 && 'Review detected rubric structure and set metadata before importing.'}
          </DialogDescription>
        </DialogHeader>

        {stepIndicator}

        {/* Step 1: Upload / Paste */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="yaml-file">Upload YAML file</Label>
              <input
                id="yaml-file"
                type="file"
                accept=".yaml,.yml"
                onChange={handleFileChange}
                className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary-foreground hover:file:bg-primary/90"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="yaml-content">Or paste YAML content</Label>
              <Textarea
                id="yaml-content"
                placeholder="Paste YAML rubric content here..."
                value={yamlContent}
                onChange={(e) => {
                  setYamlContent(e.target.value);
                  setError(null);
                }}
                rows={10}
                className="font-mono text-sm max-h-[40vh] overflow-y-auto resize-y"
              />
            </div>

            <p className="text-xs text-muted-foreground">
              Supports rubric-kit, Geval metrics, and ls-eval system config formats.
            </p>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>
        )}

        {/* Step 2: Preview & Confirm */}
        {step === 2 && analyzeResult && (
          <div className="space-y-4">
            {/* Format badge */}
            <div className="flex items-center gap-2">
              <Label className="text-xs">Detected Format:</Label>
              <Badge variant="secondary" data-testid="format-badge">
                {FORMAT_LABELS[analyzeResult.detected_format] ?? analyzeResult.detected_format}
              </Badge>
            </div>

            {/* Metric selector (only for multi-metric configs) */}
            {analyzeResult.metrics.length > 1 && (
              <div className="space-y-2">
                <Label htmlFor="metric-select">Select Metric</Label>
                <Select value={String(selectedMetricIndex)} onValueChange={handleMetricChange}>
                  <SelectTrigger id="metric-select" data-testid="metric-select">
                    <SelectValue placeholder="Select metric..." />
                  </SelectTrigger>
                  <SelectContent>
                    {analyzeResult.metrics.map((metric, idx) => (
                      <SelectItem key={metric.metric_id ?? idx} value={String(idx)}>
                        {metric.suggested_name}
                        {metric.metric_id ? ` (${metric.metric_id})` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Dimensions preview */}
            {selectedMetric && (
              <div className="space-y-2">
                <Label>
                  Dimensions ({selectedMetric.dimensions_preview.length}) &middot;{' '}
                  {selectedMetric.criteria_count} criteria total
                </Label>
                <div className="space-y-1">
                  {selectedMetric.dimensions_preview.map((dim) => (
                    <div
                      key={dim.name}
                      className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
                    >
                      <span className="font-medium truncate">{dim.name}</span>
                      <Badge variant="secondary" className="shrink-0 text-xs">
                        {dim.criteria_count} criteria
                      </Badge>
                      <span className="text-xs text-muted-foreground truncate">
                        {dim.description}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Name input */}
            <div className="space-y-2">
              <Label htmlFor="rubric-name">Name *</Label>
              <Input
                id="rubric-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Rubric name"
                required
                aria-required="true"
                data-testid="rubric-name-input"
              />
            </div>

            {/* Description textarea */}
            <div className="space-y-2">
              <Label htmlFor="rubric-description">Description</Label>
              <Textarea
                id="rubric-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                rows={2}
              />
            </div>

            {/* Tags input */}
            <div className="space-y-2">
              <Label htmlFor="rubric-tags">Tags (comma-separated)</Label>
              <Input
                id="rubric-tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="tag1, tag2, tag3"
              />
            </div>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>
        )}

        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            {step > 1 && (
              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
                data-testid="back-button"
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                Back
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            {step === 1 && (
              <Button
                type="button"
                disabled={!yamlContent.trim() || isAnalyzing}
                onClick={handleAnalyze}
                data-testid="analyze-button"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze'
                )}
              </Button>
            )}
            {step === 2 && (
              <Button
                type="button"
                disabled={!name.trim() || isImporting}
                onClick={handleImport}
                data-testid="import-button"
              >
                {isImporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  'Import'
                )}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
