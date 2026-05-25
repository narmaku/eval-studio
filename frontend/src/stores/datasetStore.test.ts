import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useDatasetStore } from './datasetStore';
import type { Dataset, DatasetDetail } from '@/types';

vi.mock('@/services/api', () => ({
  api: {
    listDatasets: vi.fn(),
    getDataset: vi.fn(),
    createDataset: vi.fn(),
    deleteDataset: vi.fn(),
  },
}));

import { api } from '@/services/api';

const mockedApi = vi.mocked(api);

const makeDataset = (overrides: Partial<Dataset> = {}): Dataset => ({
  id: 'ds-1',
  name: 'Test Dataset',
  description: 'A test dataset',
  format: 'qa_pairs',
  version: '1.0',
  tags: [],
  source_type: 'upload',
  item_count: 5,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

const makeDatasetDetail = (overrides: Partial<DatasetDetail> = {}): DatasetDetail => ({
  ...makeDataset(),
  items: [
    {
      id: 'item-1',
      question: 'What is Linux?',
      expected_answer: 'An operating system kernel',
      metadata: {},
    },
  ],
  ...overrides,
});

describe('datasetStore', () => {
  beforeEach(() => {
    useDatasetStore.setState({
      datasets: [],
      currentDataset: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useDatasetStore.getState();
    expect(state.datasets).toEqual([]);
    expect(state.currentDataset).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  describe('fetchDatasets', () => {
    it('populates datasets from API response', async () => {
      const datasets = [makeDataset({ id: 'ds-1' }), makeDataset({ id: 'ds-2' })];
      mockedApi.listDatasets.mockResolvedValue({
        items: datasets,
        total: 2,
        page: 1,
        page_size: 20,
        pages: 1,
      });

      await useDatasetStore.getState().fetchDatasets();

      const state = useDatasetStore.getState();
      expect(state.datasets).toEqual(datasets);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('sets error on API failure', async () => {
      mockedApi.listDatasets.mockRejectedValue(new Error('Network error'));

      await useDatasetStore.getState().fetchDatasets();

      const state = useDatasetStore.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });
  });

  describe('fetchDataset', () => {
    it('sets currentDataset with detail data', async () => {
      const detail = makeDatasetDetail();
      mockedApi.getDataset.mockResolvedValue(detail);

      await useDatasetStore.getState().fetchDataset('ds-1');

      const state = useDatasetStore.getState();
      expect(state.currentDataset).toEqual(detail);
      expect(state.isLoading).toBe(false);
    });

    it('sets error on API failure', async () => {
      mockedApi.getDataset.mockRejectedValue(new Error('Not found'));

      await useDatasetStore.getState().fetchDataset('ds-999');

      const state = useDatasetStore.getState();
      expect(state.error).toBe('Not found');
      expect(state.isLoading).toBe(false);
    });
  });

  describe('uploadDataset', () => {
    it('prepends new dataset to list on success', async () => {
      const existing = makeDataset({ id: 'ds-existing' });
      useDatasetStore.setState({ datasets: [existing] });

      const newDataset = makeDataset({ id: 'ds-new', name: 'New Dataset' });
      mockedApi.createDataset.mockResolvedValue(newDataset);

      const result = await useDatasetStore.getState().uploadDataset({
        name: 'New Dataset',
        format: 'qa_pairs',
        items: [],
      });

      const state = useDatasetStore.getState();
      expect(result).toEqual(newDataset);
      expect(state.datasets).toHaveLength(2);
      expect(state.datasets[0]).toEqual(newDataset);
    });

    it('sets error and re-throws on failure', async () => {
      mockedApi.createDataset.mockRejectedValue(new Error('Validation error'));

      await expect(
        useDatasetStore.getState().uploadDataset({
          name: 'Bad',
          format: 'qa_pairs',
        }),
      ).rejects.toThrow('Validation error');

      expect(useDatasetStore.getState().error).toBe('Validation error');
    });
  });

  describe('removeDataset', () => {
    it('removes dataset from list on success', async () => {
      const ds1 = makeDataset({ id: 'ds-1' });
      const ds2 = makeDataset({ id: 'ds-2' });
      useDatasetStore.setState({ datasets: [ds1, ds2] });
      mockedApi.deleteDataset.mockResolvedValue(undefined);

      await useDatasetStore.getState().removeDataset('ds-1');

      const state = useDatasetStore.getState();
      expect(state.datasets).toHaveLength(1);
      expect(state.datasets[0].id).toBe('ds-2');
    });

    it('clears currentDataset if it matches the removed id', async () => {
      const detail = makeDatasetDetail({ id: 'ds-1' });
      useDatasetStore.setState({
        datasets: [makeDataset({ id: 'ds-1' })],
        currentDataset: detail,
      });
      mockedApi.deleteDataset.mockResolvedValue(undefined);

      await useDatasetStore.getState().removeDataset('ds-1');

      expect(useDatasetStore.getState().currentDataset).toBeNull();
    });

    it('sets error and re-throws on failure', async () => {
      useDatasetStore.setState({ datasets: [makeDataset({ id: 'ds-1' })] });
      mockedApi.deleteDataset.mockRejectedValue(new Error('Forbidden'));

      await expect(useDatasetStore.getState().removeDataset('ds-1')).rejects.toThrow(
        'Forbidden',
      );

      expect(useDatasetStore.getState().error).toBe('Forbidden');
    });
  });
});
