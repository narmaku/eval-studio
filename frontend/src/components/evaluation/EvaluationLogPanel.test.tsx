import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvaluationLogPanel } from './EvaluationLogPanel';
import type { LogEntry } from '@/types';

vi.mock('@/stores/evaluationStore', () => ({
  useEvaluationStore: vi.fn(),
}));

import { useEvaluationStore } from '@/stores/evaluationStore';

const mockedUseEvaluationStore = vi.mocked(useEvaluationStore);

function createLogEntry(overrides: Partial<LogEntry> = {}): LogEntry {
  return {
    type: 'log',
    evaluation_id: 'eval-123',
    timestamp: '2026-06-02T10:00:00Z',
    level: 'info',
    message: 'Test log message',
    ...overrides,
  };
}

describe('EvaluationLogPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty state when no logs', () => {
    mockedUseEvaluationStore.mockReturnValue([]);

    render(<EvaluationLogPanel />);

    expect(screen.getByText('Waiting for logs...')).toBeInTheDocument();
  });

  it('renders log entries with timestamps', () => {
    const logs = [
      createLogEntry({ message: 'Starting evaluation', timestamp: '2026-06-02T10:00:00Z' }),
      createLogEntry({ message: 'Processing item 1', timestamp: '2026-06-02T10:00:01Z' }),
    ];
    mockedUseEvaluationStore.mockReturnValue(logs);

    render(<EvaluationLogPanel />);

    expect(screen.getByText(/Starting evaluation/)).toBeInTheDocument();
    expect(screen.getByText(/Processing item 1/)).toBeInTheDocument();
  });

  it('displays log level labels', () => {
    const logs = [
      createLogEntry({ level: 'info', message: 'Info message' }),
      createLogEntry({ level: 'warning', message: 'Warning message' }),
      createLogEntry({ level: 'error', message: 'Error message' }),
    ];
    mockedUseEvaluationStore.mockReturnValue(logs);

    render(<EvaluationLogPanel />);

    expect(screen.getByText('INFO')).toBeInTheDocument();
    expect(screen.getByText('WARN')).toBeInTheDocument();
    expect(screen.getByText('ERROR')).toBeInTheDocument();
  });

  it('applies error styling to error-level logs', () => {
    const logs = [createLogEntry({ level: 'error', message: 'Something broke' })];
    mockedUseEvaluationStore.mockReturnValue(logs);

    render(<EvaluationLogPanel />);

    const errorBadge = screen.getByText('ERROR');
    expect(errorBadge.className).toContain('text-red');
  });

  it('applies warning styling to warning-level logs', () => {
    const logs = [createLogEntry({ level: 'warning', message: 'Slow response' })];
    mockedUseEvaluationStore.mockReturnValue(logs);

    render(<EvaluationLogPanel />);

    const warnBadge = screen.getByText('WARN');
    expect(warnBadge.className).toContain('text-yellow');
  });

  it('limits displayed logs to 500 entries', () => {
    const logs = Array.from({ length: 600 }, (_, i) =>
      createLogEntry({ message: `Log entry ${i}` }),
    );
    mockedUseEvaluationStore.mockReturnValue(logs);

    render(<EvaluationLogPanel />);

    // Should show the last 500 entries
    expect(screen.getByText(/Log entry 599/)).toBeInTheDocument();
    expect(screen.queryByText(/Log entry 99$/)).not.toBeInTheDocument();
  });
});
