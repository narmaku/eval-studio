import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ToolCallCard } from './ToolCallCard';
import { Wrench } from 'lucide-react';
import type { ToolCall } from '@/types';

interface ToolInspectorProps {
  toolCalls: ToolCall[];
}

export function ToolInspector({ toolCalls }: ToolInspectorProps) {
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Wrench className="h-4 w-4" />
          Tool Calls
          {toolCalls.length > 0 && (
            <Badge variant="secondary" className="ml-1">
              {toolCalls.length}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto p-4">
        {toolCalls.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">No tool calls yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} messageId={tc.message_id} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
