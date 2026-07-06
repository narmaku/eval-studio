import { useRef, useEffect, useState, useCallback } from 'react';
import { useEvaluationStore } from '@/stores/evaluationStore';
import type { LogEntry, LogLevel } from '@/types';

const MAX_DISPLAYED_LOGS = 500;

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleTimeString('en-US', { hour12: false });
  } catch {
    return iso;
  }
}

function getLevelClasses(
  level: LogLevel,
  message: string,
): { labelClass: string; label: string; messageClass: string } {
  if (message.toLowerCase().includes('(pass)') || level === ('pass' as LogLevel)) {
    return { labelClass: 'text-pass', label: 'PASS', messageClass: 'text-foreground' };
  }
  if (message.toLowerCase().startsWith('evaluation completed')) {
    return { labelClass: 'text-accent', label: 'DONE', messageClass: 'text-accent' };
  }
  switch (level) {
    case 'warning':
      return { labelClass: 'text-warn', label: 'WARN', messageClass: 'text-text-2' };
    case 'error':
      return { labelClass: 'text-fail', label: 'ERROR', messageClass: 'text-fail' };
    default:
      return { labelClass: 'text-text-3', label: 'INFO', messageClass: 'text-text-2' };
  }
}

function LogEntryRow({ entry }: { entry: LogEntry }) {
  const { labelClass, label, messageClass } = getLevelClasses(entry.level, entry.message);
  return (
    <div className="flex gap-3 py-0.5 leading-relaxed">
      <span className="shrink-0 text-text-3">{formatTimestamp(entry.timestamp)}</span>
      <span className={`shrink-0 w-10 font-semibold ${labelClass}`}>{label}</span>
      <span className={`break-all ${messageClass}`}>{entry.message}</span>
    </div>
  );
}

export function EvaluationLogPanel() {
  const logs = useEvaluationStore((state) => state.logs);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const displayedLogs = logs.length > MAX_DISPLAYED_LOGS ? logs.slice(-MAX_DISPLAYED_LOGS) : logs;

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs.length, autoScroll]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(isAtBottom);
  }, []);

  if (logs.length === 0) {
    return (
      <div className="bg-surface-2 px-5 py-6">
        <p className="font-mono text-[11.5px] text-text-3">Waiting for logs...</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="bg-surface-2 px-5 py-3 font-mono text-[11.5px] max-h-[360px] overflow-y-auto"
      data-testid="evaluation-log-panel"
    >
      {displayedLogs.map((entry, idx) => (
        <LogEntryRow key={`${entry.timestamp}-${idx}`} entry={entry} />
      ))}
    </div>
  );
}
