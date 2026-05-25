import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PassFailChart } from './PassFailChart';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

describe('PassFailChart', () => {
  it('renders with passed=8, failed=2 without crash', () => {
    const { container } = render(<PassFailChart passedItems={8} failedItems={2} />);
    expect(screen.getByText('Pass / Fail')).toBeInTheDocument();
    expect(container.querySelector('[data-slot="card"]')).toBeInTheDocument();
  });

  it('renders with all passed (failed=0)', () => {
    render(<PassFailChart passedItems={10} failedItems={0} />);
    expect(screen.getByText('Pass / Fail')).toBeInTheDocument();
  });

  it('renders with all failed (passed=0)', () => {
    render(<PassFailChart passedItems={0} failedItems={10} />);
    expect(screen.getByText('Pass / Fail')).toBeInTheDocument();
  });

  it('renders empty state when total is zero', () => {
    render(<PassFailChart passedItems={0} failedItems={0} />);
    expect(screen.getByText('No score data available.')).toBeInTheDocument();
  });
});
