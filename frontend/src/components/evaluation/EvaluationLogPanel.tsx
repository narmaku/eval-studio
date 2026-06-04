import { useRef, useEffect, useState, useCallback } from 'react';
import { useEvaluationStore } from '@/stores/evaluationStore';
import type { LogEntry, LogLevel } from '@/types';

const MAX_DISPLAYED_LOGS = 500;

const levelStyles: Record<LogLevel, string> = {
  info: 'text-zinc-400',
  warning: 'text-yellow-500',
  error: 'text-red-500',
};

const levelLabels: Record<LogLevel, string> = {
  info: 'INFO',
  warning: 'WARN',
  error: 'ERROR',
};

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleTimeString('en-US', { hour12: false });
  } catch {
    return iso;
  }
}

function LogEntryRow({ entry }: { entry: LogEntry }) {
  return (
    <div className="flex gap-2 py-0.5 leading-tight">
      <span className="text-zinc-500 shrink-0">[{formatTimestamp(entry.timestamp)}]</span>
      <span className={`shrink-0 font-semibold ${levelStyles[entry.level]}`}>
        {levelLabels[entry.level]}
      </span>
      <span className="text-zinc-200 break-all">{entry.message}</span>
    </div>
  );
}

export function EvaluationLogPanel() {
  const logs = useEvaluationStore((state) => state.logs);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const displayedLogs = logs.length > MAX_DISPLAYED_LOGS ? logs.slice(-MAX_DISPLAYED_LOGS) : logs;

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs.length, autoScroll]);

  // Detect if user scrolled up
  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(isAtBottom);
  }, []);

  if (logs.length === 0) {
    return (
      <div className="rounded-md border bg-muted/30 p-4">
        <p className="text-sm text-muted-foreground font-mono">Waiting for logs...</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="rounded-md border bg-zinc-950 p-3 font-mono text-xs max-h-80 overflow-y-auto"
      data-testid="evaluation-log-panel"
    >
      {displayedLogs.map((entry, idx) => (
        <LogEntryRow key={`${entry.timestamp}-${idx}`} entry={entry} />
      ))}
    </div>
  );
}
