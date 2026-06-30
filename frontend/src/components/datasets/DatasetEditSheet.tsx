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
import { useDatasetStore } from '@/stores/datasetStore';
import type { Dataset } from '@/types';

interface DatasetEditSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dataset: Dataset;
}

function DatasetEditForm({ dataset, onSaved }: { dataset: Dataset; onSaved: () => void }) {
  const [name, setName] = useState(dataset.name);
  const [description, setDescription] = useState(dataset.description ?? '');
  const [tags, setTags] = useState<string[]>(dataset.tags ?? []);
  const [isSaving, setIsSaving] = useState(false);
  const updateDataset = useDatasetStore((s) => s.updateDataset);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateDataset(dataset.id, { name, description, tags });
      toast.success('Dataset updated');
      onSaved();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update dataset');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4 p-4">
      <div className="space-y-2">
        <Label htmlFor="dataset-name">Name</Label>
        <Input id="dataset-name" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="dataset-description">Description</Label>
        <Textarea
          id="dataset-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description..."
        />
      </div>
      <div className="space-y-2">
        <Label>Tags</Label>
        <TagEditor tags={tags} onChange={setTags} />
      </div>
      <Button onClick={() => void handleSave()} disabled={isSaving || !name.trim()}>
        {isSaving ? 'Saving...' : 'Save Changes'}
      </Button>
    </div>
  );
}

export function DatasetEditSheet({ open, onOpenChange, dataset }: DatasetEditSheetProps) {
  const [formKey, setFormKey] = useState(0);

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) setFormKey((k) => k + 1);
    onOpenChange(nextOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Edit Dataset</SheetTitle>
          <SheetDescription>Update dataset name, description, and tags.</SheetDescription>
        </SheetHeader>
        {open && (
          <DatasetEditForm key={formKey} dataset={dataset} onSaved={() => onOpenChange(false)} />
        )}
      </SheetContent>
    </Sheet>
  );
}
