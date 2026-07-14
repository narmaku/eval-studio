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

  it('keeps the build-time version when response has no version field', async () => {
    mockGetHealth.mockResolvedValue({ status: 'healthy' });

    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => {
      expect(mockGetHealth).toHaveBeenCalledTimes(1);
    });

    // version field missing → should keep build-time version
    expect(result.current).toMatch(/^\d+\.\d+/);
  });

  it('keeps the build-time version when backend returns empty version', async () => {
    mockGetHealth.mockResolvedValue({ status: 'healthy', version: '' });

    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => {
      expect(mockGetHealth).toHaveBeenCalledTimes(1);
    });

    // empty string is falsy → should keep build-time version
    expect(result.current).toMatch(/^\d+\.\d+/);
  });

  it('does not update state after unmount', async () => {
    let resolveHealth!: (value: { status: string; version: string }) => void;
    mockGetHealth.mockReturnValue(
      new Promise((resolve) => {
        resolveHealth = resolve;
      }),
    );

    const { result, unmount } = renderHook(() => useAppVersion());
    expect(result.current).toMatch(/^\d+\.\d+/);

    // Unmount before the promise resolves
    unmount();
    resolveHealth({ status: 'healthy', version: '9.9.9' });

    // Give the microtask queue a tick to process the resolved promise
    await waitFor(() => {
      expect(mockGetHealth).toHaveBeenCalledTimes(1);
    });

    // The version should NOT have been updated to 9.9.9 because the
    // component was unmounted (cancelled flag prevents setState)
    expect(result.current).not.toBe('9.9.9');
  });

  it('calls getHealth exactly once', async () => {
    mockGetHealth.mockResolvedValue({ status: 'healthy', version: '1.0.0' });

    renderHook(() => useAppVersion());

    await waitFor(() => {
      expect(mockGetHealth).toHaveBeenCalledTimes(1);
    });

    // Empty dependency array ensures single call
    expect(mockGetHealth).toHaveBeenCalledTimes(1);
  });
});
