import { render, screen, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ContestantSpecsCard } from './ContestantSpecsCard';
import type { EvaluationConfig } from '@/types';

const makeConfig = (contestants: EvaluationConfig['contestants']): EvaluationConfig => ({
  model_endpoint: { name: 'Test', default_model: 'test' },
  judge_config: {},
  contestants,
});

describe('ContestantSpecsCard', () => {
  it('renders contestant model names as column headers', () => {
    const config = makeConfig([
      { name: 'OpenAI', default_model: 'gpt-4o', provider_id: 'openai' },
      { name: 'Anthropic', default_model: 'claude-3', provider_id: 'anthropic' },
    ]);

    render(<ContestantSpecsCard config={config} />);

    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('claude-3')).toBeInTheDocument();
  });

  it('shows matching fields in shared section', () => {
    const config = makeConfig([
      { name: 'A', default_model: 'gpt-4o', provider_id: 'openai', tags: ['prod'] },
      { name: 'B', default_model: 'claude-3', provider_id: 'openai', tags: ['prod'] },
    ]);

    render(<ContestantSpecsCard config={config} />);

    // provider is 'openai' for both — should appear in shared section
    expect(screen.getByText('Shared')).toBeInTheDocument();
  });

  it('shows differing fields with highlight', () => {
    const config = makeConfig([
      { name: 'OpenAI', default_model: 'gpt-4o', provider_id: 'openai' },
      { name: 'Anthropic', default_model: 'claude-3', provider_id: 'anthropic' },
    ]);

    render(<ContestantSpecsCard config={config} />);

    // 'provider' should be in the Differences section
    expect(screen.getByText('Differences')).toBeInTheDocument();

    // Both provider values should be visible
    const table = screen.getByRole('table');
    expect(within(table).getByText('openai')).toBeInTheDocument();
    expect(within(table).getByText('anthropic')).toBeInTheDocument();
  });

  it('returns null when no contestants', () => {
    const config = makeConfig(undefined);
    const { container } = render(<ContestantSpecsCard config={config} />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null when contestants is empty', () => {
    const config = makeConfig([]);
    const { container } = render(<ContestantSpecsCard config={config} />);
    expect(container.innerHTML).toBe('');
  });

  it('handles single contestant gracefully', () => {
    const config = makeConfig([{ name: 'OpenAI', default_model: 'gpt-4o', provider_id: 'openai' }]);

    render(<ContestantSpecsCard config={config} />);

    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('Contestant Specs')).toBeInTheDocument();
  });

  it('shows fields unique to some contestants in differences', () => {
    const config = makeConfig([
      { name: 'A', default_model: 'gpt-4o', provider_id: 'openai', tags: ['v1'] },
      { name: 'B', default_model: 'claude-3', provider_id: 'anthropic' },
    ]);

    render(<ContestantSpecsCard config={config} />);

    // 'tags' only exists for contestant A, should show in differences
    const table = screen.getByRole('table');
    expect(within(table).getByText('tags')).toBeInTheDocument();
  });

  it('filters out sensitive keys from display', () => {
    const config = makeConfig([
      {
        name: 'A',
        default_model: 'gpt-4o',
        api_base: 'https://secret.com',
        api_key_env: 'MY_KEY',
      },
    ]);

    render(<ContestantSpecsCard config={config} />);

    expect(screen.queryByText('https://secret.com')).not.toBeInTheDocument();
    expect(screen.queryByText('MY_KEY')).not.toBeInTheDocument();
  });
});
