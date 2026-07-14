import { useCallback } from 'react';
import { Plus, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import type { MetadataEntry } from '@/components/evaluation/runDetailsUtils';

const MAX_METADATA_ENTRIES = 20;
const MAX_KEY_LENGTH = 50;
const MAX_VALUE_LENGTH = 200;

interface MetadataEditorProps {
  entries: MetadataEntry[];
  onChange: (entries: MetadataEntry[]) => void;
  /** Label rendered above the editor. Defaults to "Metadata". */
  label?: string;
  /** Placeholder shown when there are no entries. */
  emptyText?: string;
}

export function MetadataEditor({
  entries,
  onChange,
  label = 'Metadata',
  emptyText = 'No metadata entries. Click Add to include key-value pairs.',
}: MetadataEditorProps): React.JSX.Element {
  const handleAdd = useCallback(() => {
    if (entries.length >= MAX_METADATA_ENTRIES) return;
    onChange([...entries, { key: '', value: '' }]);
  }, [entries, onChange]);

  const handleRemove = useCallback(
    (index: number) => {
      onChange(entries.filter((_, i) => i !== index));
    },
    [entries, onChange],
  );

  const handleChange = useCallback(
    (index: number, field: 'key' | 'value', raw: string) => {
      const maxLen = field === 'key' ? MAX_KEY_LENGTH : MAX_VALUE_LENGTH;
      const value = raw.slice(0, maxLen);
      const updated = entries.map((entry, i) =>
        i === index ? { ...entry, [field]: value } : entry,
      );
      onChange(updated);
    },
    [entries, onChange],
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs"
          onClick={handleAdd}
          disabled={entries.length >= MAX_METADATA_ENTRIES}
        >
          <Plus className="mr-1 h-3 w-3" />
          Add
        </Button>
      </div>

      {entries.length === 0 && <p className="text-xs text-muted-foreground">{emptyText}</p>}

      {entries.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <Input
            value={entry.key}
            onChange={(e) => handleChange(index, 'key', e.target.value)}
            placeholder="Key"
            className="h-7 text-xs flex-1"
            aria-label={`Metadata key ${index + 1}`}
          />
          <Input
            value={entry.value}
            onChange={(e) => handleChange(index, 'value', e.target.value)}
            placeholder="Value"
            className="h-7 text-xs flex-[2]"
            aria-label={`Metadata value ${index + 1}`}
          />
          <button
            type="button"
            onClick={() => handleRemove(index)}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={`Remove metadata entry ${index + 1}`}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
