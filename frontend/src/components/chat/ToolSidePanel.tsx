import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Wrench } from 'lucide-react';
import { ToolInspector } from './ToolInspector';
import type { ToolCall } from '@/types';

interface ToolSidePanelProps {
  toolCalls: ToolCall[];
}

export function ToolSidePanel({ toolCalls }: ToolSidePanelProps) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="relative flex" data-testid="tool-side-panel">
      {/* Toggle button */}
      <div className="flex flex-col items-center pt-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-label={isOpen ? 'Collapse tool panel' : 'Expand tool panel'}
        >
          {isOpen ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
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
        className="overflow-hidden transition-all duration-200"
        style={{ width: isOpen ? '400px' : '0px' }}
      >
        {isOpen && (
          <div className="h-full w-[400px]">
            <ToolInspector toolCalls={toolCalls} />
          </div>
        )}
      </div>
    </div>
  );
}
