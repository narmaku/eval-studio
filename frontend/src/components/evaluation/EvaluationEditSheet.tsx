import { useState } from 'react';
import { toast } from 'sonner';

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
import { MetadataEditor } from '@/components/ui/MetadataEditor';
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
      <MetadataEditor
        entries={metadataEntries}
        onChange={setMetadataEntries}
        emptyText="No metadata entries."
      />
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
