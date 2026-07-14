import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { cn } from '@/lib/utils';
import { Bot, User, Monitor, Scale } from 'lucide-react';
import type { Message } from '@/types';

interface ChatMessageProps {
  message: Message;
  renderMarkdown?: boolean;
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

export function ChatMessage({ message, renderMarkdown }: ChatMessageProps) {
  const config = senderConfig[message.sender] ?? defaultConfig;
  const Icon = config.icon;
  const useMarkdown = renderMarkdown && message.sender !== 'user';

  const formattedTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={cn('flex flex-col gap-1', config.align)} data-message-id={message.id}>
      <div className="flex items-center gap-1.5">
        <Icon className={cn('h-3 w-3', config.accent)} />
        <span className={cn('text-xs font-medium', config.accent)}>{config.label}</span>
        <span className="text-xs text-muted-foreground">{formattedTime}</span>
      </div>
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-3 py-2 text-sm',
          config.bg,
          useMarkdown
            ? 'prose prose-sm dark:prose-invert max-w-none [&_pre]:overflow-x-auto [&_table]:text-xs [&_pre]:text-xs [&_pre]:bg-background/50 [&_pre]:rounded [&_pre]:p-2'
            : 'whitespace-pre-wrap',
        )}
      >
        {useMarkdown ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        ) : (
          message.content
        )}
      </div>
    </div>
  );
}
