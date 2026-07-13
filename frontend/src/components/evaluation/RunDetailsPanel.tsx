import { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, Plus, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { MetadataEntry } from './runDetailsUtils';

const MAX_METADATA_ENTRIES = 20;
const MAX_KEY_LENGTH = 50;
const MAX_VALUE_LENGTH = 200;

interface RunDetailsPanelProps {
  title: string;
  onTitleChange: (title: string) => void;
  description: string;
  onDescriptionChange: (description: string) => void;
  metadata: MetadataEntry[];
  onMetadataChange: (entries: MetadataEntry[]) => void;
}

export function RunDetailsPanel({
  title,
  onTitleChange,
  description,
  onDescriptionChange,
  metadata,
  onMetadataChange,
}: RunDetailsPanelProps): React.JSX.Element {
  const [open, setOpen] = useState(false);

  const activeCount =
    (title.trim() ? 1 : 0) +
    (description.trim() ? 1 : 0) +
    metadata.filter((e) => e.key.trim()).length;

  const handleAddEntry = useCallback(() => {
    if (metadata.length >= MAX_METADATA_ENTRIES) return;
    onMetadataChange([...metadata, { key: '', value: '' }]);
  }, [metadata, onMetadataChange]);

  const handleRemoveEntry = useCallback(
    (index: number) => {
      onMetadataChange(metadata.filter((_, i) => i !== index));
    },
    [metadata, onMetadataChange],
  );

  const handleEntryChange = useCallback(
    (index: number, field: 'key' | 'value', raw: string) => {
      const maxLen = field === 'key' ? MAX_KEY_LENGTH : MAX_VALUE_LENGTH;
      const value = raw.slice(0, maxLen);
      const updated = metadata.map((entry, i) =>
        i === index ? { ...entry, [field]: value } : entry,
      );
      onMetadataChange(updated);
    },
    [metadata, onMetadataChange],
  );

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50"
        >
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          Run Details
          {activeCount > 0 && (
            <span className="ml-auto rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
              {activeCount} set
            </span>
          )}
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="space-y-4 border-x border-b rounded-b-md px-3 py-3">
          <div className="space-y-1">
            <Label htmlFor="run-title" className="text-xs">
              Title
            </Label>
            <Input
              id="run-title"
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              placeholder="Auto-generated if empty"
              className="h-8 text-sm"
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="run-description" className="text-xs">
              Description
            </Label>
            <Textarea
              id="run-description"
              value={description}
              onChange={(e) => onDescriptionChange(e.target.value)}
              placeholder="Optional description for this evaluation run..."
              rows={2}
              className="text-sm"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs">Metadata</Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={handleAddEntry}
                disabled={metadata.length >= MAX_METADATA_ENTRIES}
              >
                <Plus className="mr-1 h-3 w-3" />
                Add
              </Button>
            </div>

            {metadata.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No metadata entries. Click Add to include key-value pairs.
              </p>
            )}

            {metadata.map((entry, index) => (
              <div key={index} className="flex items-center gap-2">
                <Input
                  value={entry.key}
                  onChange={(e) => handleEntryChange(index, 'key', e.target.value)}
                  placeholder="Key"
                  className="h-7 text-xs flex-1"
                  aria-label={`Metadata key ${index + 1}`}
                />
                <Input
                  value={entry.value}
                  onChange={(e) => handleEntryChange(index, 'value', e.target.value)}
                  placeholder="Value"
                  className="h-7 text-xs flex-[2]"
                  aria-label={`Metadata value ${index + 1}`}
                />
                <button
                  type="button"
                  onClick={() => handleRemoveEntry(index)}
                  className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label={`Remove metadata entry ${index + 1}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
