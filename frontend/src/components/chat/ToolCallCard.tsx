import { useState, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronRight, ChevronDown, MessageSquare, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { ToolCall } from '@/types';

interface ToolCallCardProps {
  toolCall: ToolCall;
  messageId?: string;
}

function formatDuration(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${ms}ms`;
}

export function ToolCallCard({ toolCall, messageId }: ToolCallCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const resolvedMessageId = messageId ?? toolCall.message_id;

  const handleShowInChat = useCallback(() => {
    if (!resolvedMessageId) return;
    const el = document.querySelector(`[data-message-id="${resolvedMessageId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [resolvedMessageId]);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-lg border">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted/50 transition-colors"
            aria-label={toolCall.tool_name}
          >
            {isOpen ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            )}
            <span className="font-mono font-medium truncate">{toolCall.tool_name}</span>
            <span className="ml-auto flex items-center gap-1.5 shrink-0">
              {toolCall.status === 'executing' ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground">Executing...</span>
                </>
              ) : toolCall.status === 'error' ? (
                <>
                  <XCircle className="h-3.5 w-3.5 text-destructive" />
                  <span className="text-[10px] text-destructive">Error</span>
                </>
              ) : toolCall.status === 'completed' ? (
                <>
                  <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  {toolCall.duration_ms != null && (
                    <Badge variant="secondary" className="text-[10px]">
                      {formatDuration(toolCall.duration_ms)}
                    </Badge>
                  )}
                </>
              ) : (
                <Badge variant="secondary" className="text-[10px]">
                  {toolCall.duration_ms != null ? formatDuration(toolCall.duration_ms) : 'Pending'}
                </Badge>
              )}
            </span>
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t px-3 py-2 space-y-2">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Arguments</p>
              <pre className="text-xs bg-muted rounded p-2 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(toolCall.arguments, null, 2)}
              </pre>
            </div>
            {toolCall.result !== undefined && toolCall.result !== null && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">Result</p>
                <pre className="max-h-[200px] overflow-y-auto text-xs bg-muted rounded p-2 overflow-x-auto whitespace-pre-wrap">
                  {typeof toolCall.result === 'string'
                    ? toolCall.result
                    : JSON.stringify(toolCall.result, null, 2)}
                </pre>
              </div>
            )}
            {resolvedMessageId && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1.5 text-xs text-muted-foreground"
                onClick={handleShowInChat}
              >
                <MessageSquare className="h-3 w-3" />
                Show in chat
              </Button>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}
