import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useDatasetStore } from './datasetStore';
import type { Dataset, DatasetDetail, AnalyzeResponse } from '@/types';

vi.mock('@/services/api', () => ({
  api: {
    listDatasets: vi.fn(),
    getDataset: vi.fn(),
    createDataset: vi.fn(),
    deleteDataset: vi.fn(),
    analyzeDatasetFiles: vi.fn(),
    importDataset: vi.fn(),
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
      order_index: 0,
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
      analysisResult: null,
      isAnalyzing: false,
      isImporting: false,
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
      expect(state.datasets[0]?.id).toBe('ds-2');
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

      await expect(useDatasetStore.getState().removeDataset('ds-1')).rejects.toThrow('Forbidden');

      expect(useDatasetStore.getState().error).toBe('Forbidden');
    });
  });

  describe('analyzeFiles', () => {
    const makeAnalyzeResponse = (): AnalyzeResponse => ({
      analysis_id: 'analysis-1',
      files: [
        {
          filename: 'test.yaml',
          format: 'yaml',
          field_count: 2,
          row_count: 5,
          fields: ['question', 'expected_answer'],
          sample_rows: [{ question: 'Q1', expected_answer: 'A1' }],
          errors: [],
        },
      ],
      merged_fields: ['question', 'expected_answer'],
      suggested_mapping: {
        question_field: 'question',
        answer_field: 'expected_answer',
        metadata_fields: [],
        confidence: 0.95,
      },
      total_rows: 5,
    });

    it('sets analysisResult on success', async () => {
      const response = makeAnalyzeResponse();
      mockedApi.analyzeDatasetFiles.mockResolvedValue(response);

      const files = [new File(['content'], 'test.yaml')];
      await useDatasetStore.getState().analyzeFiles(files);

      const state = useDatasetStore.getState();
      expect(state.analysisResult).toEqual(response);
      expect(state.isAnalyzing).toBe(false);
      expect(state.error).toBeNull();
    });

    it('sets isAnalyzing during analysis', async () => {
      let resolvePromise: (value: AnalyzeResponse) => void;
      const promise = new Promise<AnalyzeResponse>((resolve) => {
        resolvePromise = resolve;
      });
      mockedApi.analyzeDatasetFiles.mockReturnValue(promise);

      const files = [new File(['content'], 'test.yaml')];
      const analyzePromise = useDatasetStore.getState().analyzeFiles(files);

      expect(useDatasetStore.getState().isAnalyzing).toBe(true);

      resolvePromise!(makeAnalyzeResponse());
      await analyzePromise;

      expect(useDatasetStore.getState().isAnalyzing).toBe(false);
    });

    it('sets error and re-throws on failure', async () => {
      mockedApi.analyzeDatasetFiles.mockRejectedValue(new Error('Bad format'));

      const files = [new File(['content'], 'test.yaml')];
      await expect(useDatasetStore.getState().analyzeFiles(files)).rejects.toThrow('Bad format');

      const state = useDatasetStore.getState();
      expect(state.error).toBe('Bad format');
      expect(state.isAnalyzing).toBe(false);
    });
  });

  describe('smartImport', () => {
    it('prepends dataset and clears analysis on success', async () => {
      const existing = makeDataset({ id: 'ds-existing' });
      useDatasetStore.setState({
        datasets: [existing],
        analysisResult: {
          analysis_id: 'analysis-1',
          files: [],
          merged_fields: [],
          suggested_mapping: {
            question_field: 'q',
            answer_field: 'a',
            metadata_fields: [],
            confidence: 0.9,
          },
          total_rows: 0,
        },
      });

      const newDataset = makeDataset({ id: 'ds-imported', name: 'Imported' });
      mockedApi.importDataset.mockResolvedValue(newDataset);

      const result = await useDatasetStore.getState().smartImport({
        analysis_id: 'analysis-1',
        name: 'Imported',
        mapping: { question_field: 'q', answer_field: 'a' },
        merge_mode: 'single',
      });

      const state = useDatasetStore.getState();
      expect(result).toEqual(newDataset);
      expect(state.datasets).toHaveLength(2);
      expect(state.datasets[0]).toEqual(newDataset);
      expect(state.analysisResult).toBeNull();
      expect(state.isImporting).toBe(false);
    });

    it('sets error and re-throws on failure', async () => {
      mockedApi.importDataset.mockRejectedValue(new Error('Import failed'));

      await expect(
        useDatasetStore.getState().smartImport({
          analysis_id: 'analysis-1',
          name: 'Test',
          mapping: { question_field: 'q', answer_field: 'a' },
          merge_mode: 'single',
        }),
      ).rejects.toThrow('Import failed');

      const state = useDatasetStore.getState();
      expect(state.error).toBe('Import failed');
      expect(state.isImporting).toBe(false);
    });
  });

  describe('clearAnalysis', () => {
    it('resets analysis state', () => {
      useDatasetStore.setState({
        analysisResult: {
          analysis_id: 'analysis-1',
          files: [],
          merged_fields: [],
          suggested_mapping: {
            question_field: 'q',
            answer_field: 'a',
            metadata_fields: [],
            confidence: 0.9,
          },
          total_rows: 0,
        },
        isAnalyzing: true,
      });

      useDatasetStore.getState().clearAnalysis();

      const state = useDatasetStore.getState();
      expect(state.analysisResult).toBeNull();
      expect(state.isAnalyzing).toBe(false);
    });
  });
});
