import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { HarnessSelector } from './HarnessSelector';

// Mock the harnessStore
const mockFetchHarnesses = vi.fn();

vi.mock('@/stores/harnessStore', () => ({
  useHarnessStore: vi.fn(() => ({
    harnesses: [
      {
        id: 'builtin-litellm',
        name: 'Built-in Agent (LiteLLM)',
        type: 'builtin',
        binary_path: null,
        description: 'LiteLLM-based agent',
        supported_features: ['streaming', 'tool_calls'],
        output_format: null,
        default: true,
        enabled: true,
        version: null,
      },
      {
        id: 'goose-cli',
        name: 'Goose CLI Agent',
        type: 'subprocess',
        binary_path: 'goose',
        description: 'Block Goose AI coding agent',
        supported_features: ['tool_calls'],
        output_format: 'goose',
        default: false,
        enabled: false,
        version: null,
      },
    ],
    isLoading: false,
    error: null,
    fetchHarnesses: mockFetchHarnesses,
  })),
}));

describe('HarnessSelector', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the harness selector when multiple harnesses are available', () => {
    render(<HarnessSelector value="builtin-litellm" onChange={mockOnChange} />);
    expect(screen.getByText('Agent Harness')).toBeInTheDocument();
  });

  it('fetches harnesses on mount', () => {
    render(<HarnessSelector onChange={mockOnChange} />);
    expect(mockFetchHarnesses).toHaveBeenCalled();
  });

  it('shows loading state', async () => {
    // Override mock for this test
    const { useHarnessStore } = await import('@/stores/harnessStore');
    vi.mocked(useHarnessStore).mockReturnValueOnce({
      harnesses: [],
      isLoading: true,
      error: null,
      fetchHarnesses: mockFetchHarnesses,
      checkHarness: vi.fn(),
    });

    render(<HarnessSelector onChange={mockOnChange} />);
    expect(screen.getByText('Loading harnesses...')).toBeInTheDocument();
  });

  it('returns null when only one harness exists', async () => {
    const { useHarnessStore } = await import('@/stores/harnessStore');
    vi.mocked(useHarnessStore).mockReturnValueOnce({
      harnesses: [
        {
          id: 'builtin-litellm',
          name: 'Built-in Agent',
          type: 'builtin' as const,
          binary_path: null,
          description: '',
          supported_features: [],
          output_format: null,
          default: true,
          enabled: true,
          version: null,
        },
      ],
      isLoading: false,
      error: null,
      fetchHarnesses: mockFetchHarnesses,
      checkHarness: vi.fn(),
    });

    const { container } = render(<HarnessSelector onChange={mockOnChange} />);
    // Should render nothing
    expect(container.innerHTML).toBe('');
  });
});
