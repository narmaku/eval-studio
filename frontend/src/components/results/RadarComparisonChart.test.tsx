import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RadarComparisonChart } from './RadarComparisonChart';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

describe('RadarComparisonChart', () => {
  it('renders with valid multi-metric data', () => {
    const series = [
      { name: 'model-a', data: { faithfulness: 0.9, relevance: 0.7, clarity: 0.8 } },
      { name: 'model-b', data: { faithfulness: 0.6, relevance: 0.8, clarity: 0.5 } },
    ];

    render(<RadarComparisonChart series={series} title="Test Radar" />);

    expect(screen.getByText('Test Radar')).toBeInTheDocument();
  });

  it('renders with default title when not provided', () => {
    const series = [
      { name: 'model-a', data: { accuracy: 0.8, fluency: 0.7 } },
    ];

    render(<RadarComparisonChart series={series} />);

    expect(screen.getByText('Metric Comparison')).toBeInTheDocument();
  });

  it('returns null when fewer than 2 metrics', () => {
    const series = [
      { name: 'model-a', data: { only_one: 0.5 } },
    ];

    const { container } = render(<RadarComparisonChart series={series} />);

    // Should render nothing
    expect(container.innerHTML).toBe('');
  });

  it('returns null when no series provided', () => {
    const { container } = render(<RadarComparisonChart series={[]} />);

    expect(container.innerHTML).toBe('');
  });

  it('renders with exactly 2 metrics (minimum for radar)', () => {
    const series = [
      { name: 'model-a', data: { metric1: 0.5, metric2: 0.8 } },
    ];

    render(<RadarComparisonChart series={series} />);

    expect(screen.getByText('Metric Comparison')).toBeInTheDocument();
  });

  it('handles series with different metric keys', () => {
    const series = [
      { name: 'model-a', data: { accuracy: 0.8, clarity: 0.7 } as Record<string, number> },
      { name: 'model-b', data: { accuracy: 0.6, fluency: 0.9 } as Record<string, number> },
    ];

    // Should render with all 3 unique metrics (accuracy, clarity, fluency)
    render(<RadarComparisonChart series={series} title="Mixed Metrics" />);

    expect(screen.getByText('Mixed Metrics')).toBeInTheDocument();
  });
});
