import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Plus, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { TagEditor } from '@/components/ui/tag-editor';
import { useEvaluationStore } from '@/stores/evaluationStore';
import {
  recordToMetadataEntries,
  metadataEntriesToRecord,
} from '@/components/evaluation/runDetailsUtils';
import type { Evaluation } from '@/types';

interface EvaluationEditSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  evaluation: Evaluation;
}

function EvaluationEditForm({
  evaluation,
  onSaved,
}: {
  evaluation: Evaluation;
  onSaved: () => void;
}) {
  const [name, setName] = useState(evaluation.name);
  const [description, setDescription] = useState(evaluation.description ?? '');
  const [tags, setTags] = useState<string[]>(evaluation.tags ?? []);
  const [metadataEntries, setMetadataEntries] = useState(
    recordToMetadataEntries(evaluation.metadata),
  );
  const [isSaving, setIsSaving] = useState(false);
  const updateEvaluation = useEvaluationStore((s) => s.updateEvaluation);

  const handleAddMetadata = useCallback(() => {
    if (metadataEntries.length >= 20) return;
    setMetadataEntries([...metadataEntries, { key: '', value: '' }]);
  }, [metadataEntries]);

  const handleRemoveMetadata = useCallback(
    (index: number) => {
      setMetadataEntries(metadataEntries.filter((_, i) => i !== index));
    },
    [metadataEntries],
  );

  const handleMetadataChange = useCallback(
    (index: number, field: 'key' | 'value', raw: string) => {
      const maxLen = field === 'key' ? 50 : 200;
      const value = raw.slice(0, maxLen);
      setMetadataEntries(
        metadataEntries.map((entry, i) => (i === index ? { ...entry, [field]: value } : entry)),
      );
    },
    [metadataEntries],
  );

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateEvaluation(evaluation.id, {
        name,
        description,
        tags,
        metadata: metadataEntriesToRecord(metadataEntries) ?? {},
      });
      toast.success('Evaluation updated');
      onSaved();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update evaluation');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4 p-4">
      <div className="space-y-2">
        <Label htmlFor="eval-name">Name</Label>
        <Input id="eval-name" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="eval-description">Description</Label>
        <Textarea
          id="eval-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description..."
        />
      </div>
      <div className="space-y-2">
        <Label>Tags</Label>
        <TagEditor tags={tags} onChange={setTags} />
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Metadata</Label>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={handleAddMetadata}
            disabled={metadataEntries.length >= 20}
          >
            <Plus className="mr-1 h-3 w-3" />
            Add
          </Button>
        </div>
        {metadataEntries.length === 0 && (
          <p className="text-xs text-muted-foreground">No metadata entries.</p>
        )}
        {metadataEntries.map((entry, index) => (
          <div key={index} className="flex items-center gap-2">
            <Input
              value={entry.key}
              onChange={(e) => handleMetadataChange(index, 'key', e.target.value)}
              placeholder="Key"
              className="h-7 text-xs flex-1"
              aria-label={`Metadata key ${index + 1}`}
            />
            <Input
              value={entry.value}
              onChange={(e) => handleMetadataChange(index, 'value', e.target.value)}
              placeholder="Value"
              className="h-7 text-xs flex-[2]"
              aria-label={`Metadata value ${index + 1}`}
            />
            <button
              type="button"
              onClick={() => handleRemoveMetadata(index)}
              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label={`Remove metadata entry ${index + 1}`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
      <Button onClick={() => void handleSave()} disabled={isSaving || !name.trim()}>
        {isSaving ? 'Saving...' : 'Save Changes'}
      </Button>
    </div>
  );
}

export function EvaluationEditSheet({ open, onOpenChange, evaluation }: EvaluationEditSheetProps) {
  const [formKey, setFormKey] = useState(0);

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) setFormKey((k) => k + 1);
    onOpenChange(nextOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Edit Evaluation</SheetTitle>
          <SheetDescription>
            Update evaluation name, description, tags, and metadata.
          </SheetDescription>
        </SheetHeader>
        {open && (
          <EvaluationEditForm
            key={formKey}
            evaluation={evaluation}
            onSaved={() => onOpenChange(false)}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}
