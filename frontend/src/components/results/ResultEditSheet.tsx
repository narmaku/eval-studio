import { useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { TagEditor } from '@/components/ui/tag-editor';
import { useResultStore } from '@/stores/resultStore';
import type { Result } from '@/types';

interface ResultEditSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: Result;
}

function ResultEditForm({ result, onSaved }: { result: Result; onSaved: () => void }) {
  const [name, setName] = useState(result.name ?? '');
  const [tags, setTags] = useState<string[]>(result.tags ?? []);
  const [isSaving, setIsSaving] = useState(false);
  const updateResult = useResultStore((s) => s.updateResult);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateResult(result.id, { name: name || undefined, tags });
      toast.success('Result updated');
      onSaved();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update result');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4 p-4">
      <div className="space-y-2">
        <Label htmlFor="result-name">Name</Label>
        <Input
          id="result-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Result name..."
        />
      </div>
      <div className="space-y-2">
        <Label>Tags</Label>
        <TagEditor tags={tags} onChange={setTags} />
      </div>
      <Button onClick={() => void handleSave()} disabled={isSaving}>
        {isSaving ? 'Saving...' : 'Save Changes'}
      </Button>
    </div>
  );
}

export function ResultEditSheet({ open, onOpenChange, result }: ResultEditSheetProps) {
  const [formKey, setFormKey] = useState(0);

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) setFormKey((k) => k + 1);
    onOpenChange(nextOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Edit Result</SheetTitle>
          <SheetDescription>Update result name and tags.</SheetDescription>
        </SheetHeader>
        {open && (
          <ResultEditForm key={formKey} result={result} onSaved={() => onOpenChange(false)} />
        )}
      </SheetContent>
    </Sheet>
  );
}
