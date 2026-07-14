import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { MetadataEditor } from '@/components/ui/MetadataEditor';
import type { MetadataEntry } from './runDetailsUtils';

interface RunDetailsPanelProps {
  title: string;
  onTitleChange: (title: string) => void;
  /** When omitted, the description field is hidden. */
  description?: string;
  onDescriptionChange?: (description: string) => void;
  /** When omitted, the metadata section is hidden. */
  metadata?: MetadataEntry[];
  onMetadataChange?: (entries: MetadataEntry[]) => void;
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

  const showDescription = description !== undefined && onDescriptionChange !== undefined;
  const showMetadata = metadata !== undefined && onMetadataChange !== undefined;

  const activeCount =
    (title.trim() ? 1 : 0) +
    (showDescription && description.trim() ? 1 : 0) +
    (showMetadata ? metadata.filter((e) => e.key.trim()).length : 0);

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

          {showDescription && (
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
          )}

          {showMetadata && <MetadataEditor entries={metadata} onChange={onMetadataChange} />}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
