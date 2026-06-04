import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useProviderStore } from './providerStore';

vi.mock('@/services/api', () => ({
  api: {
    listProviders: vi.fn(),
    createProvider: vi.fn(),
    updateProvider: vi.fn(),
    deleteProvider: vi.fn(),
  },
}));

import { api } from '@/services/api';
import type { Provider, CreateProviderRequest } from '@/types';

const mockedApi = vi.mocked(api);

const makeProvider = (overrides: Partial<Provider> = {}): Provider => ({
  id: 'p-1',
  name: 'Test Provider',
  litellm_model: 'openai/gpt-4',
  api_base: null,
  has_api_key: false,
  proxy: null,
  ssl_cert_path: null,
  tags: [],
  purpose: 'test',
  default_params: null,
  ...overrides,
});

describe('providerStore', () => {
  beforeEach(() => {
    useProviderStore.setState({
      providers: [],
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useProviderStore.getState();
    expect(state.providers).toEqual([]);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  describe('fetchProviders', () => {
    it('sets loading, stores providers, clears loading on success', async () => {
      const mockProviders = [makeProvider(), makeProvider({ id: 'p-2', name: 'Second' })];
      mockedApi.listProviders.mockResolvedValue(mockProviders);

      const promise = useProviderStore.getState().fetchProviders();
      expect(useProviderStore.getState().isLoading).toBe(true);
      expect(useProviderStore.getState().error).toBeNull();

      await promise;

      expect(useProviderStore.getState().isLoading).toBe(false);
      expect(useProviderStore.getState().providers).toEqual(mockProviders);
      expect(mockedApi.listProviders).toHaveBeenCalledWith(undefined);
    });

    it('passes purpose filter when provided', async () => {
      mockedApi.listProviders.mockResolvedValue([]);

      await useProviderStore.getState().fetchProviders('judge');

      expect(mockedApi.listProviders).toHaveBeenCalledWith('judge');
    });

    it('handles API error: sets error string', async () => {
      mockedApi.listProviders.mockRejectedValue(new Error('Network error'));

      await useProviderStore.getState().fetchProviders();

      expect(useProviderStore.getState().isLoading).toBe(false);
      expect(useProviderStore.getState().error).toBe('Network error');
      expect(useProviderStore.getState().providers).toEqual([]);
    });
  });

  describe('createProvider', () => {
    it('calls API and adds provider to store', async () => {
      const request: CreateProviderRequest = {
        name: 'New Provider',
        litellm_model: 'openai/gpt-4',
      };
      const created = makeProvider({ id: 'p-new', name: 'New Provider' });
      mockedApi.createProvider.mockResolvedValue(created);

      const result = await useProviderStore.getState().createProvider(request);

      expect(result).toEqual(created);
      expect(useProviderStore.getState().providers).toContainEqual(created);
      expect(mockedApi.createProvider).toHaveBeenCalledWith(request);
    });

    it('throws on API error', async () => {
      mockedApi.createProvider.mockRejectedValue(new Error('Create failed'));

      await expect(
        useProviderStore.getState().createProvider({
          name: 'Bad',
          litellm_model: 'x',
        }),
      ).rejects.toThrow('Create failed');
    });
  });

  describe('updateProvider', () => {
    it('calls API and updates provider in store', async () => {
      const existing = makeProvider({ id: 'p-1', name: 'Old Name' });
      useProviderStore.setState({ providers: [existing] });

      const updated = makeProvider({ id: 'p-1', name: 'New Name' });
      mockedApi.updateProvider.mockResolvedValue(updated);

      const result = await useProviderStore.getState().updateProvider('p-1', { name: 'New Name' });

      expect(result).toEqual(updated);
      const providers = useProviderStore.getState().providers;
      expect(providers).toHaveLength(1);
      expect(providers[0]!.name).toBe('New Name');
      expect(mockedApi.updateProvider).toHaveBeenCalledWith('p-1', { name: 'New Name' });
    });
  });

  describe('deleteProvider', () => {
    it('calls API and removes provider from store', async () => {
      const provider = makeProvider({ id: 'p-1' });
      useProviderStore.setState({ providers: [provider] });
      mockedApi.deleteProvider.mockResolvedValue(undefined);

      await useProviderStore.getState().deleteProvider('p-1');

      expect(useProviderStore.getState().providers).toEqual([]);
      expect(mockedApi.deleteProvider).toHaveBeenCalledWith('p-1');
    });
  });
});
