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
import { useSessionHistoryStore } from '@/stores/sessionHistoryStore';
import type { Session } from '@/types';

interface SessionEditSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  session: Session;
}

function SessionEditForm({ session, onSaved }: { session: Session; onSaved: () => void }) {
  const [name, setName] = useState(session.name ?? '');
  const [tags, setTags] = useState<string[]>(session.tags ?? []);
  const [isSaving, setIsSaving] = useState(false);
  const updateSession = useSessionHistoryStore((s) => s.updateSession);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateSession(session.id, { name: name || undefined, tags });
      toast.success('Session updated');
      onSaved();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update session');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4 p-4">
      <div className="space-y-2">
        <Label htmlFor="session-name">Name</Label>
        <Input
          id="session-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Session name..."
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

export function SessionEditSheet({ open, onOpenChange, session }: SessionEditSheetProps) {
  const [formKey, setFormKey] = useState(0);

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) setFormKey((k) => k + 1);
    onOpenChange(nextOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Edit Session</SheetTitle>
          <SheetDescription>Update session name and tags.</SheetDescription>
        </SheetHeader>
        {open && (
          <SessionEditForm key={formKey} session={session} onSaved={() => onOpenChange(false)} />
        )}
      </SheetContent>
    </Sheet>
  );
}
