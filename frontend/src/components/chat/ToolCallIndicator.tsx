import { Wrench, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolCall, ToolCallStatus } from '@/types';

interface ToolCallIndicatorProps {
  toolCalls: ToolCall[];
  onSelect: (toolCall: ToolCall) => void;
  selectedToolId?: string;
}

function StatusIcon({ status }: { status?: ToolCallStatus }): React.ReactElement | null {
  switch (status) {
    case 'executing':
      return (
        <Loader2
          className="h-3 w-3 animate-spin text-muted-foreground"
          data-testid="status-executing"
        />
      );
    case 'completed':
      return <CheckCircle className="h-3 w-3 text-green-500" data-testid="status-completed" />;
    case 'error':
      return <XCircle className="h-3 w-3 text-destructive" data-testid="status-error" />;
    default:
      return null;
  }
}

export function ToolCallIndicator({
  toolCalls,
  onSelect,
  selectedToolId,
}: ToolCallIndicatorProps): React.ReactElement | null {
  if (toolCalls.length === 0) return null;

  return (
    <div className="flex items-center justify-center gap-1 py-1" data-testid="tool-call-indicator">
      <Wrench className="h-3 w-3 text-muted-foreground shrink-0" />
      <div className="flex flex-wrap items-center gap-1">
        {toolCalls.map((tc) => {
          const isSelected = selectedToolId === tc.id;
          return (
            <button
              key={tc.id}
              type="button"
              data-testid={`tool-chip-${tc.id}`}
              className={cn(
                'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs',
                'transition-colors hover:bg-muted/80 cursor-pointer',
                isSelected
                  ? 'ring-2 ring-primary bg-muted border-primary/50'
                  : 'bg-muted/50 border-border',
              )}
              onClick={() => onSelect(tc)}
            >
              <span className="font-mono truncate max-w-[120px]">{tc.tool_name}</span>
              <StatusIcon status={tc.status} />
            </button>
          );
        })}
      </div>
    </div>
  );
}
