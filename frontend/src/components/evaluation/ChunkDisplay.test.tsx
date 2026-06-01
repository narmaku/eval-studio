import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { ChunkDisplay } from './ChunkDisplay';
import type { RetrievedChunk } from '@/types';

const mockChunks: RetrievedChunk[] = [
  {
    content: 'This is a short chunk about systemd services.',
    source: 'rhel-docs/systemd.md',
    relevance_score: 0.95,
  },
  {
    content: 'This chunk discusses firewall configuration and port management on RHEL systems.',
    source: 'rhel-docs/firewall.md',
    relevance_score: 0.55,
  },
  {
    content: 'Low relevance chunk about unrelated topic.',
    relevance_score: 0.2,
  },
  {
    content: 'A chunk without any relevance score at all.',
  },
];

describe('ChunkDisplay', () => {
  it('renders all chunks', () => {
    render(<ChunkDisplay chunks={mockChunks} />);

    expect(screen.getByText('Chunk 1')).toBeInTheDocument();
    expect(screen.getByText('Chunk 2')).toBeInTheDocument();
    expect(screen.getByText('Chunk 3')).toBeInTheDocument();
    expect(screen.getByText('Chunk 4')).toBeInTheDocument();
  });

  it('displays chunk content', () => {
    render(<ChunkDisplay chunks={mockChunks} />);

    expect(screen.getByText('This is a short chunk about systemd services.')).toBeInTheDocument();
  });

  it('displays source when present', () => {
    render(<ChunkDisplay chunks={mockChunks} />);

    expect(screen.getByText('rhel-docs/systemd.md')).toBeInTheDocument();
    expect(screen.getByText('rhel-docs/firewall.md')).toBeInTheDocument();
  });

  it('shows green badge for high relevance score (>0.7)', () => {
    render(<ChunkDisplay chunks={mockChunks} />);

    const badge = screen.getByTestId('chunk-score-0');
    expect(badge).toHaveTextContent('95%');
    expect(badge.className).toContain('green');
  });

  it('shows yellow badge for medium relevance score (>0.4)', () => {
    render(<ChunkDisplay chunks={mockChunks} />);

    const badge = screen.getByTestId('chunk-score-1');
    expect(badge).toHaveTextContent('55%');
    expect(badge.className).toContain('yellow');
  });

  it('shows red badge for low relevance score (<=0.4)', () => {
    render(<ChunkDisplay chunks={mockChunks} />);

    const badge = screen.getByTestId('chunk-score-2');
    expect(badge).toHaveTextContent('20%');
    expect(badge.className).toContain('red');
  });

  it('shows gray badge when no relevance score', () => {
    render(<ChunkDisplay chunks={mockChunks} />);

    const badge = screen.getByTestId('chunk-score-3');
    expect(badge).toHaveTextContent('N/A');
    expect(badge.className).toContain('gray');
  });

  it('shows empty state when no chunks provided', () => {
    render(<ChunkDisplay chunks={[]} />);

    expect(screen.getByText('No chunks retrieved.')).toBeInTheDocument();
  });

  it('truncates long content and shows expand button', () => {
    const longContent = 'A'.repeat(300);
    const longChunks: RetrievedChunk[] = [{ content: longContent }];

    render(<ChunkDisplay chunks={longChunks} />);

    expect(screen.getByText(/Show more/)).toBeInTheDocument();
  });

  it('expands truncated content on click', async () => {
    const user = userEvent.setup();
    const longContent = 'START ' + 'A'.repeat(300) + ' END';
    const longChunks: RetrievedChunk[] = [{ content: longContent }];

    render(<ChunkDisplay chunks={longChunks} />);

    // Initially truncated - END should not be visible
    expect(screen.queryByText(/END/)).not.toBeInTheDocument();

    // Click show more
    await user.click(screen.getByText(/Show more/));

    // Now full content should be visible
    expect(screen.getByText(/END/)).toBeInTheDocument();
    expect(screen.getByText(/Show less/)).toBeInTheDocument();
  });
});
