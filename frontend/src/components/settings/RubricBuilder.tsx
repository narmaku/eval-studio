import { useState, useEffect, useCallback } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { X, Plus } from 'lucide-react';
import { useRubricStore } from '@/stores/rubricStore';
import type { Rubric, RubricDimension, CreateRubricRequest } from '@/types';

interface RubricBuilderProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rubric?: Rubric;
  onSaved?: () => void;
}

interface FormDimension {
  name: string;
  weight: string;
  description: string;
}

export function RubricBuilder({ open, onOpenChange, rubric, onSaved }: RubricBuilderProps) {
  const createRubric = useRubricStore((s) => s.createRubric);
  const updateRubric = useRubricStore((s) => s.updateRubric);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [dimensions, setDimensions] = useState<FormDimension[]>([]);
  const [passThreshold, setPassThreshold] = useState('0.7');
  const [aggregation, setAggregation] = useState('weighted_average');
  const [promptTemplate, setPromptTemplate] = useState('');
  const [errors, setErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  const isEditMode = !!rubric;

  const resetForm = useCallback(() => {
    if (rubric) {
      setName(rubric.name);
      setDescription(rubric.description ?? '');
      setDimensions(
        rubric.dimensions.map((d) => ({
          name: d.name,
          weight: String(d.weight),
          description: d.description,
        }))
      );
      setPassThreshold(String(rubric.pass_threshold));
      setAggregation(rubric.aggregation);
      setPromptTemplate(rubric.prompt_template ?? '');
    } else {
      setName('');
      setDescription('');
      setDimensions([]);
      setPassThreshold('0.7');
      setAggregation('weighted_average');
      setPromptTemplate('');
    }
    setErrors([]);
  }, [rubric]);

  useEffect(() => {
    if (open) {
      resetForm();
    }
  }, [open, resetForm]);

  const addDimension = () => {
    setDimensions((prev) => [...prev, { name: '', weight: '1.0', description: '' }]);
  };

  const removeDimension = (index: number) => {
    setDimensions((prev) => prev.filter((_, i) => i !== index));
  };

  const updateDimension = (index: number, field: keyof FormDimension, value: string) => {
    setDimensions((prev) => prev.map((d, i) => (i === index ? { ...d, [field]: value } : d)));
  };

  const validate = (): boolean => {
    const newErrors: string[] = [];

    if (!name.trim()) {
      newErrors.push('Name is required');
    }

    if (dimensions.length === 0) {
      newErrors.push('At least one dimension is required');
    }

    dimensions.forEach((d, i) => {
      const weight = parseFloat(d.weight);
      if (isNaN(weight) || weight <= 0) {
        newErrors.push(`Dimension ${i + 1}: weight must be a positive number`);
      }
    });

    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    setIsSaving(true);
    try {
      const parsedDimensions: RubricDimension[] = dimensions.map((d) => ({
        name: d.name,
        weight: parseFloat(d.weight) || 1.0,
        description: d.description,
      }));

      const data: CreateRubricRequest = {
        name: name.trim(),
        description: description.trim() || null,
        dimensions: parsedDimensions,
        pass_threshold: parseFloat(passThreshold) || 0.7,
        aggregation,
        prompt_template: promptTemplate.trim() || null,
      };

      if (isEditMode && rubric) {
        await updateRubric(rubric.id, data);
      } else {
        await createRubric(data);
      }

      onSaved?.();
      onOpenChange(false);
    } catch {
      setErrors(['Failed to save rubric. Please try again.']);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEditMode ? 'Edit Rubric' : 'New Rubric'}</SheetTitle>
        </SheetHeader>

        <div className="space-y-6 px-4 pb-4">
          {errors.length > 0 && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {errors.map((e, i) => (
                <p key={i}>{e}</p>
              ))}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="rubric-name">Name</Label>
            <Input
              id="rubric-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., RHEL Support Quality"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="rubric-description">Description</Label>
            <Textarea
              id="rubric-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description of this rubric"
              rows={2}
            />
          </div>

          <Separator />

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Dimensions</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addDimension}
              >
                <Plus className="mr-1 h-4 w-4" />
                Add Dimension
              </Button>
            </div>

            {dimensions.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No dimensions added yet. Click &quot;Add Dimension&quot; to start.
              </p>
            )}

            {dimensions.map((dim, index) => (
              <div key={index} data-testid="dimension-row" className="space-y-2 rounded-md border p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">
                    Dimension {index + 1}
                  </span>
                  <button
                    type="button"
                    data-testid="remove-dimension"
                    onClick={() => removeDimension(index)}
                    className="text-muted-foreground hover:text-destructive"
                    aria-label={`Remove dimension ${index + 1}`}
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="grid grid-cols-[1fr_80px] gap-2">
                  <Input
                    placeholder="Dimension name"
                    value={dim.name}
                    onChange={(e) => updateDimension(index, 'name', e.target.value)}
                  />
                  <Input
                    type="number"
                    placeholder="Weight"
                    step="0.1"
                    min="0"
                    value={dim.weight}
                    onChange={(e) => updateDimension(index, 'weight', e.target.value)}
                  />
                </div>
                <Input
                  placeholder="Description (optional)"
                  value={dim.description}
                  onChange={(e) => updateDimension(index, 'description', e.target.value)}
                />
              </div>
            ))}
          </div>

          <Separator />

          <div className="space-y-2">
            <p className="text-sm font-medium">Pass Threshold</p>
            <Input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={passThreshold}
              onChange={(e) => setPassThreshold(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Score required to pass (0.0 - 1.0)
            </p>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">Aggregation</p>
            <Select value={aggregation} onValueChange={setAggregation}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="weighted_average">Weighted Average</SelectItem>
                <SelectItem value="average">Average</SelectItem>
                <SelectItem value="min">Minimum</SelectItem>
                <SelectItem value="max">Maximum</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="rubric-prompt">Prompt Template (optional)</Label>
            <Textarea
              id="rubric-prompt"
              value={promptTemplate}
              onChange={(e) => setPromptTemplate(e.target.value)}
              placeholder="Custom prompt template for this rubric"
              rows={3}
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button onClick={handleSave} disabled={isSaving} className="flex-1">
              {isSaving ? 'Saving...' : 'Save'}
            </Button>
            <Button variant="outline" onClick={() => onOpenChange(false)} className="flex-1">
              Cancel
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
