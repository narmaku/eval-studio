import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useAppVersion } from './useAppVersion';

const mockGetHealth = vi.fn();

vi.mock('@/services/api', () => ({
  api: {
    getHealth: () => mockGetHealth(),
  },
}));

describe('useAppVersion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns the build-time version initially', () => {
    mockGetHealth.mockReturnValue(new Promise(() => {})); // never resolves
    const { result } = renderHook(() => useAppVersion());
    expect(result.current).toMatch(/^\d+\.\d+/);
  });

  it('returns the backend version after a successful health fetch', async () => {
    mockGetHealth.mockResolvedValue({ status: 'healthy', version: '2.5.0' });

    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => {
      expect(result.current).toBe('2.5.0');
    });
  });

  it('keeps the build-time version when the health endpoint fails', async () => {
    mockGetHealth.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useAppVersion());

    // Wait a tick to let the effect settle
    await waitFor(() => {
      expect(mockGetHealth).toHaveBeenCalledTimes(1);
    });

    // Should still show the build-time version, not crash
    expect(result.current).toMatch(/^\d+\.\d+/);
  });
});
