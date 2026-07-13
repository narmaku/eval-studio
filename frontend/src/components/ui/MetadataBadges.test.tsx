import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { MetadataBadges } from './MetadataBadges';

describe('MetadataBadges', () => {
  it('renders all badges when count is within maxInline', () => {
    const metadata = { provider: 'openai', model: 'gpt-4o', temperature: '0.7' };
    render(<MetadataBadges metadata={metadata} />);

    expect(screen.getByText('provider: openai')).toBeInTheDocument();
    expect(screen.getByText('model: gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('temperature: 0.7')).toBeInTheDocument();
  });

  it('shows overflow badge when exceeding maxInline', () => {
    const metadata = {
      provider: 'openai',
      model: 'gpt-4o',
      temperature: '0.7',
      top_p: '0.9',
      max_tokens: '4096',
    };
    render(<MetadataBadges metadata={metadata} maxInline={3} />);

    // First 3 should be visible
    expect(screen.getByText('provider: openai')).toBeInTheDocument();
    expect(screen.getByText('model: gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('temperature: 0.7')).toBeInTheDocument();

    // Overflow badge
    expect(screen.getByText('+2 more')).toBeInTheDocument();
  });

  it('renders nothing when metadata is empty', () => {
    const { container } = render(<MetadataBadges metadata={{}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when metadata is null', () => {
    const { container } = render(<MetadataBadges metadata={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('uses compact styling when compact prop is true', () => {
    const metadata = { provider: 'openai' };
    const { container } = render(<MetadataBadges metadata={metadata} compact />);

    // Compact badges have smaller text
    const badge = container.querySelector('[data-slot="badge"]');
    expect(badge).toBeInTheDocument();
    expect(badge?.className).toContain('text-[10px]');
  });

  it('shows all overflow badges in tooltip on hover', async () => {
    const user = userEvent.setup();
    const metadata = {
      provider: 'openai',
      model: 'gpt-4o',
      temperature: '0.7',
      top_p: '0.9',
      max_tokens: '4096',
    };
    render(<MetadataBadges metadata={metadata} maxInline={3} />);

    const overflowBadge = screen.getByText('+2 more');
    await user.hover(overflowBadge);

    // The tooltip should show the overflow items (may render more than once via portal)
    const topPElements = await screen.findAllByText(/top_p: 0.9/);
    expect(topPElements.length).toBeGreaterThanOrEqual(1);
    const maxTokensElements = await screen.findAllByText(/max_tokens: 4096/);
    expect(maxTokensElements.length).toBeGreaterThanOrEqual(1);
  });

  it('truncates long values using formatBadgeValue', () => {
    const metadata = {
      model: 'this-is-a-very-long-model-name-that-exceeds-limit',
    };
    const { container } = render(<MetadataBadges metadata={metadata} />);

    // The badge text content includes key + truncated value
    const badge = container.querySelector('[data-slot="badge"]');
    expect(badge).toBeInTheDocument();
    expect(badge?.textContent).toContain('...');
  });

  it('defaults maxInline to 4', () => {
    const metadata = {
      a: '1',
      b: '2',
      c: '3',
      d: '4',
      e: '5',
    };
    render(<MetadataBadges metadata={metadata} />);

    expect(screen.getByText('+1 more')).toBeInTheDocument();
  });
});
