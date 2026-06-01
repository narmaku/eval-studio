import { useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { MessageSquare } from 'lucide-react';
import type { Message } from '@/types';

interface ConversationPanelProps {
  messages: Message[];
  isProcessing: boolean;
  onSend: (content: string) => void;
  disabled: boolean;
}

export function ConversationPanel({
  messages,
  isProcessing,
  onSend,
  disabled,
}: ConversationPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, isProcessing]);

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <MessageSquare className="h-4 w-4" />
          Conversation
        </CardTitle>
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
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
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
      <ChatInput onSend={onSend} disabled={disabled || isProcessing} />
    </Card>
  );
}
