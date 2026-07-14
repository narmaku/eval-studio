import { useRef, useEffect, useMemo, useState } from 'react';
import { Code, FileText, MessageSquare } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ToolCallIndicator } from './ToolCallIndicator';
import type { Message, ToolCall } from '@/types';

interface ConversationPanelProps {
  messages: Message[];
  isProcessing: boolean;
  onSend: (content: string) => void;
  disabled: boolean;
  toolCalls?: ToolCall[];
  onToolSelect?: (toolCall: ToolCall) => void;
  selectedToolId?: string;
}

export function ConversationPanel({
  messages,
  isProcessing,
  onSend,
  disabled,
  toolCalls,
  onToolSelect,
  selectedToolId,
}: ConversationPanelProps) {
  const [showFormatted, setShowFormatted] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, isProcessing]);

  // Group tool calls by the message they belong to.
  // Tool calls without a message_id are attached to the last agent message.
  const toolCallsByMessageId = useMemo(() => {
    if (!toolCalls || toolCalls.length === 0) return new Map<string, ToolCall[]>();

    const grouped = new Map<string, ToolCall[]>();

    // Find the last agent message id for orphan tool calls
    let lastAgentMessageId: string | undefined;
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg && msg.sender === 'agent') {
        lastAgentMessageId = msg.id;
        break;
      }
    }

    for (const tc of toolCalls) {
      const key = tc.message_id ?? lastAgentMessageId ?? '__orphan__';
      const existing = grouped.get(key);
      if (existing) {
        existing.push(tc);
      } else {
        grouped.set(key, [tc]);
      }
    }

    return grouped;
  }, [toolCalls, messages]);

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <MessageSquare className="h-4 w-4" />
            Conversation
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-xs text-muted-foreground"
            onClick={() => setShowFormatted((prev) => !prev)}
            aria-label={showFormatted ? 'Show raw text' : 'Show formatted text'}
          >
            {showFormatted ? (
              <>
                <Code className="h-3.5 w-3.5" />
                Raw
              </>
            ) : (
              <>
                <FileText className="h-3.5 w-3.5" />
                Formatted
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && !isProcessing && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              Start a conversation by typing a message below.
            </p>
          </div>
        )}
        <div className="space-y-4">
          {messages.map((message) => {
            const indicatorToolCalls = toolCallsByMessageId.get(message.id);
            return (
              <div key={message.id}>
                <ChatMessage message={message} renderMarkdown={showFormatted} />
                {indicatorToolCalls && indicatorToolCalls.length > 0 && onToolSelect && (
                  <div className="mt-2">
                    <ToolCallIndicator
                      toolCalls={indicatorToolCalls}
                      onSelect={onToolSelect}
                      selectedToolId={selectedToolId}
                    />
                  </div>
                )}
              </div>
            );
          })}
          {isProcessing && (
            <div data-testid="typing-indicator" className="flex items-start gap-1.5">
              <div className="flex items-center gap-1 rounded-lg bg-muted px-3 py-2">
                <span
                  className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60"
                  style={{ animationDelay: '0ms' }}
                />
                <span
                  className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60"
                  style={{ animationDelay: '150ms' }}
                />
                <span
                  className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60"
                  style={{ animationDelay: '300ms' }}
                />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </CardContent>
      {!disabled && <ChatInput onSend={onSend} disabled={isProcessing} />}
    </Card>
  );
}
