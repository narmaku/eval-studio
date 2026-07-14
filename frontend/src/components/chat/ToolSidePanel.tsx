import { useState, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Wrench } from 'lucide-react';
import { ToolDetailPanel } from './ToolDetailPanel';
import { cn } from '@/lib/utils';
import type { ToolCall } from '@/types';

interface ToolSidePanelProps {
  toolCalls: ToolCall[];
  selectedToolId: string | null;
  onToolSelect: (toolCall: ToolCall) => void;
}

export function ToolSidePanel({ toolCalls, selectedToolId, onToolSelect }: ToolSidePanelProps) {
  const [isOpen, setIsOpen] = useState(true);

  const selectedToolCall = useMemo(() => {
    if (!selectedToolId) return null;
    return toolCalls.find((tc) => tc.id === selectedToolId) ?? null;
  }, [selectedToolId, toolCalls]);

  return (
    <div className="relative flex h-full max-w-[50%]" data-testid="tool-side-panel">
      {/* Toggle button */}
      <div className="flex flex-col items-center pt-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-label={isOpen ? 'Collapse tool panel' : 'Expand tool panel'}
        >
          {isOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
        {!isOpen && toolCalls.length > 0 && (
          <div className="mt-2 flex flex-col items-center gap-1">
            <Wrench className="h-4 w-4 text-muted-foreground" />
            <Badge variant="secondary" className="text-[10px]">
              {toolCalls.length}
            </Badge>
          </div>
        )}
      </div>

      {/* Panel content */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-200',
          isOpen ? 'flex-1 min-w-0' : 'w-0',
        )}
      >
        {isOpen && (
          <div className="h-full">
            <ToolDetailPanel
              toolCall={selectedToolCall}
              allToolCalls={toolCalls}
              onSelect={onToolSelect}
            />
          </div>
        )}
      </div>
    </div>
  );
}
