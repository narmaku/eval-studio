import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useHarnessStore } from './harnessStore';

// Mock the API
vi.mock('@/services/api', () => ({
  api: {
    listHarnesses: vi.fn(),
    checkHarness: vi.fn(),
  },
}));

describe('harnessStore', () => {
  beforeEach(() => {
    // Reset store state
    useHarnessStore.setState({
      harnesses: [],
      isLoading: false,
      error: null,
    });
  });

  it('fetchHarnesses sets harnesses on success', async () => {
    const { api } = await import('@/services/api');
    const mockHarnesses = [
      {
        id: 'builtin-litellm',
        name: 'Built-in Agent',
        type: 'builtin' as const,
        binary_path: null,
        description: 'Test',
        supported_features: ['streaming'],
        output_format: null,
        default: true,
        enabled: true,
        version: null,
      },
    ];
    vi.mocked(api.listHarnesses).mockResolvedValue(mockHarnesses);

    await useHarnessStore.getState().fetchHarnesses();

    const state = useHarnessStore.getState();
    expect(state.harnesses).toEqual(mockHarnesses);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('fetchHarnesses sets error on failure', async () => {
    const { api } = await import('@/services/api');
    vi.mocked(api.listHarnesses).mockRejectedValue(new Error('Network error'));

    await useHarnessStore.getState().fetchHarnesses();

    const state = useHarnessStore.getState();
    expect(state.harnesses).toEqual([]);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBe('Network error');
  });
});
