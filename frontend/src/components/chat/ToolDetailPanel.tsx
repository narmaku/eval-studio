import { useCallback, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Wrench,
  ChevronLeft,
  ChevronRight,
  Loader2,
  CheckCircle,
  XCircle,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolCall, ToolCallStatus } from '@/types';

interface ToolDetailPanelProps {
  toolCall: ToolCall | null;
  allToolCalls: ToolCall[];
  onSelect: (toolCall: ToolCall) => void;
}

function formatDuration(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${ms}ms`;
}

function StatusBadge({ status }: { status?: ToolCallStatus }): React.ReactElement {
  switch (status) {
    case 'executing':
      return (
        <Badge variant="secondary" className="gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          executing
        </Badge>
      );
    case 'completed':
      return (
        <Badge variant="secondary" className="gap-1 text-green-600 dark:text-green-400">
          <CheckCircle className="h-3 w-3" />
          completed
        </Badge>
      );
    case 'error':
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          error
        </Badge>
      );
    default:
      return <Badge variant="secondary">pending</Badge>;
  }
}

export function ToolDetailPanel({
  toolCall,
  allToolCalls,
  onSelect,
}: ToolDetailPanelProps): React.ReactElement {
  const currentIndex = useMemo(() => {
    if (!toolCall) return -1;
    return allToolCalls.findIndex((tc) => tc.id === toolCall.id);
  }, [toolCall, allToolCalls]);

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < allToolCalls.length - 1;

  const handlePrev = useCallback(() => {
    const prev = hasPrev ? allToolCalls[currentIndex - 1] : undefined;
    if (prev) onSelect(prev);
  }, [hasPrev, currentIndex, allToolCalls, onSelect]);

  const handleNext = useCallback(() => {
    const next = hasNext ? allToolCalls[currentIndex + 1] : undefined;
    if (next) onSelect(next);
  }, [hasNext, currentIndex, allToolCalls, onSelect]);

  if (!toolCall) {
    return (
      <Card className="flex h-full flex-col overflow-hidden">
        <CardContent className="flex flex-1 flex-col items-center justify-center gap-3 p-6">
          <Search className="h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">Click a tool call to inspect</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      {/* Mini tool list */}
      {allToolCalls.length > 1 && (
        <div className="flex flex-wrap items-center gap-1 border-b px-3 py-2">
          {allToolCalls.map((tc) => (
            <button
              key={tc.id}
              type="button"
              data-testid={`tool-pill-${tc.id}`}
              className={cn(
                'rounded-full px-2 py-0.5 text-[10px] font-mono transition-colors cursor-pointer',
                tc.id === toolCall.id
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80 text-muted-foreground',
              )}
              onClick={() => onSelect(tc)}
            >
              {tc.tool_name}
            </button>
          ))}
        </div>
      )}

      {/* Header with name + status + navigation */}
      <CardHeader className="border-b px-4 py-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Wrench className="h-4 w-4" />
            <span className="font-mono">{toolCall.tool_name}</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <StatusBadge status={toolCall.status} />
            {toolCall.duration_ms != null && toolCall.duration_ms > 0 && (
              <Badge variant="outline" className="text-[10px]">
                {formatDuration(toolCall.duration_ms)}
              </Badge>
            )}
          </div>
        </div>
        {allToolCalls.length > 1 && (
          <div className="flex items-center justify-between mt-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs"
              disabled={!hasPrev}
              onClick={handlePrev}
              aria-label="Previous tool"
            >
              <ChevronLeft className="h-3 w-3" />
              Prev
            </Button>
            <span className="text-xs text-muted-foreground">
              {currentIndex + 1} of {allToolCalls.length}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs"
              disabled={!hasNext}
              onClick={handleNext}
              aria-label="Next tool"
            >
              Next
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        )}
      </CardHeader>

      {/* Scrollable content area */}
      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Arguments</p>
          <pre className="text-xs bg-muted rounded p-2 overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </pre>
        </div>
        {toolCall.result !== undefined && toolCall.result !== null && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Result</p>
            <pre className="max-h-[300px] overflow-y-auto text-xs bg-muted rounded p-2 overflow-x-auto whitespace-pre-wrap">
              {typeof toolCall.result === 'string'
                ? toolCall.result
                : JSON.stringify(toolCall.result, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
