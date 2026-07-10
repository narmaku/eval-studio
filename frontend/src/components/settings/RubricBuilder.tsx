import { useRef, useState } from 'react';
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
import { X, Plus, ChevronDown, ChevronRight } from 'lucide-react';
import { useRubricStore } from '@/stores/rubricStore';
import type { Rubric, RubricDimension, CreateRubricRequest } from '@/types';

interface RubricBuilderProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rubric?: Rubric;
  onSaved?: () => void;
}

interface FormCriterion {
  name: string;
  criterion: string;
  weight: string;
}

interface FormDimension {
  name: string;
  weight: string;
  description: string;
  criteria: FormCriterion[];
}

/**
 * Wrapper component that controls Sheet open/close.
 * Uses a key to remount the inner form each time the sheet opens,
 * ensuring a clean state reset without useEffect or ref access during render.
 */
export function RubricBuilder({ open, onOpenChange, rubric, onSaved }: RubricBuilderProps) {
  // Increment key each time sheet opens to force inner form remount
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
          <SheetTitle>{rubric ? 'Edit Rubric' : 'New Rubric'}</SheetTitle>
        </SheetHeader>
        {open && (
          <RubricForm
            key={formKey}
            rubric={rubric}
            onSaved={onSaved}
            onClose={() => onOpenChange(false)}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}

interface RubricFormProps {
  rubric?: Rubric;
  onSaved?: () => void;
  onClose: () => void;
}

function RubricForm({ rubric, onSaved, onClose }: RubricFormProps) {
  const createRubric = useRubricStore((s) => s.createRubric);
  const updateRubric = useRubricStore((s) => s.updateRubric);

  const isEditMode = !!rubric;

  const [name, setName] = useState(rubric?.name ?? '');
  const [description, setDescription] = useState(rubric?.description ?? '');
  const [dimensions, setDimensions] = useState<FormDimension[]>(
    rubric?.dimensions.map((d) => ({
      name: d.name,
      weight: String(d.weight),
      description: d.description,
      criteria: (d.criteria ?? []).map((c) => ({
        name: c.name ?? '',
        criterion: c.criterion ?? '',
        weight: String(c.weight ?? 1),
      })),
    })) ?? [],
  );
  const [expandedCriteria, setExpandedCriteria] = useState<Set<number>>(new Set());
  const [passThreshold, setPassThreshold] = useState(String(rubric?.pass_threshold ?? 0.7));
  const [aggregation, setAggregation] = useState(rubric?.aggregation ?? 'weighted_average');
  const [promptTemplate, setPromptTemplate] = useState(rubric?.prompt_template ?? '');
  const [errors, setErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  const addDimension = () => {
    setDimensions((prev) => [...prev, { name: '', weight: '1.0', description: '', criteria: [] }]);
  };

  const removeDimension = (index: number) => {
    setDimensions((prev) => prev.filter((_, i) => i !== index));
    setExpandedCriteria((prev) => {
      const next = new Set<number>();
      for (const idx of prev) {
        if (idx < index) next.add(idx);
        else if (idx > index) next.add(idx - 1);
      }
      return next;
    });
  };

  const updateDimensionField = (index: number, field: keyof FormDimension, value: string) => {
    setDimensions((prev) => prev.map((d, i) => (i === index ? { ...d, [field]: value } : d)));
  };

  const toggleCriteriaExpanded = (dimIndex: number) => {
    setExpandedCriteria((prev) => {
      const next = new Set(prev);
      if (next.has(dimIndex)) next.delete(dimIndex);
      else next.add(dimIndex);
      return next;
    });
  };

  const addCriterion = (dimIndex: number) => {
    setDimensions((prev) =>
      prev.map((d, i) =>
        i === dimIndex
          ? { ...d, criteria: [...d.criteria, { name: '', criterion: '', weight: '1' }] }
          : d,
      ),
    );
    setExpandedCriteria((prev) => new Set(prev).add(dimIndex));
  };

  const removeCriterion = (dimIndex: number, critIndex: number) => {
    setDimensions((prev) =>
      prev.map((d, i) =>
        i === dimIndex ? { ...d, criteria: d.criteria.filter((_, j) => j !== critIndex) } : d,
      ),
    );
  };

  const updateCriterionField = (
    dimIndex: number,
    critIndex: number,
    field: keyof FormCriterion,
    value: string,
  ) => {
    setDimensions((prev) =>
      prev.map((d, i) =>
        i === dimIndex
          ? {
              ...d,
              criteria: d.criteria.map((c, j) => (j === critIndex ? { ...c, [field]: value } : c)),
            }
          : d,
      ),
    );
  };

  const formRef = useRef<HTMLDivElement>(null);

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
      d.criteria.forEach((c, j) => {
        if (!c.name.trim()) {
          newErrors.push(`Dimension ${i + 1}, Criterion ${j + 1}: name is required`);
        }
        const cWeight = parseFloat(c.weight);
        if (isNaN(cWeight) || cWeight <= 0) {
          newErrors.push(`Dimension ${i + 1}, Criterion ${j + 1}: weight must be positive`);
        }
      });
    });

    setErrors(newErrors);
    if (newErrors.length > 0) {
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    return newErrors.length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    setIsSaving(true);
    try {
      const parsedDimensions: RubricDimension[] = dimensions.map((d) => {
        const validCriteria = d.criteria
          .filter((c) => c.name.trim() || c.criterion.trim())
          .map((c) => ({
            name: c.name,
            criterion: c.criterion || c.name,
            weight: parseFloat(c.weight) || 1.0,
          }));

        return {
          name: d.name,
          weight: parseFloat(d.weight) || 1.0,
          description: d.description,
          ...(validCriteria.length > 0 && { criteria: validCriteria }),
        };
      });

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
      onClose();
    } catch {
      setErrors(['Failed to save rubric. Please try again.']);
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div ref={formRef} className="space-y-6 px-4 pb-4">
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
          <Button type="button" variant="outline" size="sm" onClick={addDimension}>
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
                onChange={(e) => updateDimensionField(index, 'name', e.target.value)}
              />
              <Input
                type="number"
                placeholder="Weight"
                step="0.1"
                min="0"
                value={dim.weight}
                onChange={(e) => updateDimensionField(index, 'weight', e.target.value)}
              />
            </div>
            <Input
              placeholder="Description (optional)"
              value={dim.description}
              onChange={(e) => updateDimensionField(index, 'description', e.target.value)}
            />

            {/* Criteria sub-editor */}
            <div className="space-y-2 pt-1">
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                  onClick={() => toggleCriteriaExpanded(index)}
                >
                  {expandedCriteria.has(index) ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                  Criteria ({dim.criteria.length})
                </button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-6 px-2 text-[11px]"
                  onClick={() => addCriterion(index)}
                >
                  <Plus className="mr-1 h-3 w-3" />
                  Add Criterion
                </Button>
              </div>

              {expandedCriteria.has(index) && dim.criteria.length > 0 && (
                <div className="space-y-2 rounded-md border border-dashed border-border bg-muted/20 p-2">
                  {dim.criteria.map((crit, critIdx) => (
                    <div
                      key={critIdx}
                      className="space-y-1.5 rounded-md border border-border bg-background p-2"
                    >
                      <div className="flex items-center gap-2">
                        <Input
                          placeholder="Criterion name"
                          className="h-7 text-xs"
                          value={crit.name}
                          onChange={(e) =>
                            updateCriterionField(index, critIdx, 'name', e.target.value)
                          }
                        />
                        <Input
                          type="number"
                          placeholder="Weight"
                          step="0.1"
                          min="0"
                          className="h-7 w-20 text-xs"
                          value={crit.weight}
                          onChange={(e) =>
                            updateCriterionField(index, critIdx, 'weight', e.target.value)
                          }
                        />
                        <button
                          type="button"
                          onClick={() => removeCriterion(index, critIdx)}
                          className="shrink-0 text-muted-foreground hover:text-destructive"
                          aria-label={`Remove criterion ${critIdx + 1}`}
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <Textarea
                        placeholder="Criterion text (evaluation instruction)"
                        rows={2}
                        className="text-xs"
                        value={crit.criterion}
                        onChange={(e) =>
                          updateCriterionField(index, critIdx, 'criterion', e.target.value)
                        }
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
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
        <p className="text-xs text-muted-foreground">Score required to pass (0.0 - 1.0)</p>
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
        <Button variant="outline" onClick={onClose} className="flex-1">
          Cancel
        </Button>
      </div>
    </div>
  );
}
