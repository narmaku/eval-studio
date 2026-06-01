import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Bot, User, Monitor, Scale } from 'lucide-react';
import type { Message } from '@/types';

interface ChatMessageProps {
  message: Message;
}

interface SenderStyle {
  icon: React.ElementType;
  label: string;
  align: string;
  bg: string;
  accent: string;
}

const defaultConfig: SenderStyle = {
  icon: Bot,
  label: 'Agent',
  align: 'items-start',
  bg: 'bg-muted',
  accent: 'text-muted-foreground',
};

const senderConfig: Record<string, SenderStyle> = {
  user: {
    icon: User,
    label: 'You',
    align: 'items-end',
    bg: 'bg-primary text-primary-foreground',
    accent: 'text-primary',
  },
  agent: {
    icon: Bot,
    label: 'Agent',
    align: 'items-start',
    bg: 'bg-muted',
    accent: 'text-muted-foreground',
  },
  system: {
    icon: Monitor,
    label: 'System',
    align: 'items-center',
    bg: 'bg-muted/50 italic',
    accent: 'text-muted-foreground',
  },
  judge: {
    icon: Scale,
    label: 'Judge',
    align: 'items-start',
    bg: 'bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800',
    accent: 'text-amber-600 dark:text-amber-400',
  },
};

export function ChatMessage({ message }: ChatMessageProps) {
  const config = senderConfig[message.sender] ?? defaultConfig;
  const Icon = config.icon;

  const formattedTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={cn('flex flex-col gap-1', config.align)}>
      <div className="flex items-center gap-1.5">
        <Icon className={cn('h-3 w-3', config.accent)} />
        <span className={cn('text-xs font-medium', config.accent)}>{config.label}</span>
        <span className="text-xs text-muted-foreground">{formattedTime}</span>
      </div>
      <div
        className={cn('max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap', config.bg)}
      >
        {message.content}
      </div>
      {message.tool_calls && message.tool_calls.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {message.tool_calls.map((tc) => (
            <Badge key={tc.id} variant="secondary" className="text-[10px]">
              {tc.tool_name}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
