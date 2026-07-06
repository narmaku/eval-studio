export type ScoreLevel = 'pass' | 'warn' | 'fail';

export function getScoreLevel(score: number | null | undefined): ScoreLevel {
  if (score == null) return 'fail';
  if (score >= 0.85) return 'pass';
  if (score >= 0.6) return 'warn';
  return 'fail';
}

export function getScoreColorClass(score: number | null | undefined): string {
  const level = getScoreLevel(score);
  return level === 'pass' ? 'text-pass' : level === 'warn' ? 'text-warn' : 'text-fail';
}

export function getModeBadgeClasses(mode: string): string {
  switch (mode) {
    case 'qa':
      return 'bg-mode-qa-bg text-mode-qa-fg';
    case 'agent':
      return 'bg-mode-agent-bg text-mode-agent-fg';
    case 'rag':
      return 'bg-mode-rag-bg text-mode-rag-fg';
    case 'arena':
      return 'bg-mode-arena-bg text-mode-arena-fg';
    default:
      return 'bg-surface-3 text-text-2';
  }
}

export function getModeLabel(mode: string): string {
  switch (mode) {
    case 'qa':
      return 'Q&A';
    case 'agent':
      return 'AGENT';
    case 'rag':
      return 'RAG';
    case 'arena':
      return 'ARENA';
    default:
      return mode.toUpperCase();
  }
}

export function getStatusPillClasses(status: string): string {
  switch (status) {
    case 'completed':
    case 'scored':
    case 'enabled':
      return 'bg-pass-bg text-pass';
    case 'running':
    case 'scoring':
      return 'bg-warn-bg text-warn';
    case 'failed':
    case 'error':
      return 'bg-fail-bg text-fail';
    case 'ended':
    case 'pending':
    default:
      return 'bg-surface-3 text-text-2';
  }
}

export function formatMonoDate(dateString: string | undefined | null): string {
  if (!dateString) return '—';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatMonoTimestamp(dateString: string | undefined | null): string {
  if (!dateString) return '—';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleString('en-US', {
    month: 'numeric',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}
