import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useRubricStore } from './rubricStore';

vi.mock('@/services/api', () => ({
  api: {
    listRubrics: vi.fn(),
    createRubric: vi.fn(),
    updateRubric: vi.fn(),
    deleteRubric: vi.fn(),
    importRubric: vi.fn(),
    generateRubric: vi.fn(),
    refineRubric: vi.fn(),
  },
}));

import { api } from '@/services/api';
import type { Rubric, CreateRubricRequest } from '@/types';

const mockedApi = vi.mocked(api);

const makeRubric = (overrides: Partial<Rubric> = {}): Rubric => ({
  id: 'r-1',
  name: 'Test Rubric',
  description: 'A test rubric',
  dimensions: [{ name: 'accuracy', weight: 1.0, description: 'Is it accurate?' }],
  pass_threshold: 0.7,
  aggregation: 'weighted_average',
  prompt_template: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('rubricStore', () => {
  beforeEach(() => {
    useRubricStore.setState({
      rubrics: [],
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has correct initial state', () => {
    const state = useRubricStore.getState();
    expect(state.rubrics).toEqual([]);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  describe('fetchRubrics', () => {
    it('sets loading, stores rubrics, clears loading on success', async () => {
      const mockRubrics = [makeRubric(), makeRubric({ id: 'r-2', name: 'Second Rubric' })];
      mockedApi.listRubrics.mockResolvedValue({
        items: mockRubrics,
        total: mockRubrics.length,
        page: 1,
        page_size: 20,
        pages: 1,
      });

      const promise = useRubricStore.getState().fetchRubrics();
      expect(useRubricStore.getState().isLoading).toBe(true);
      expect(useRubricStore.getState().error).toBeNull();

      await promise;

      expect(useRubricStore.getState().isLoading).toBe(false);
      expect(useRubricStore.getState().rubrics).toEqual(mockRubrics);
      expect(mockedApi.listRubrics).toHaveBeenCalledWith({});
    });

    it('passes name filter when provided', async () => {
      mockedApi.listRubrics.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        pages: 0,
      });

      await useRubricStore.getState().fetchRubrics('quality');

      expect(mockedApi.listRubrics).toHaveBeenCalledWith({ name: 'quality' });
    });

    it('handles API error: sets error string', async () => {
      mockedApi.listRubrics.mockRejectedValue(new Error('Network error'));

      await useRubricStore.getState().fetchRubrics();

      expect(useRubricStore.getState().isLoading).toBe(false);
      expect(useRubricStore.getState().error).toBe('Network error');
      expect(useRubricStore.getState().rubrics).toEqual([]);
    });
  });

  describe('createRubric', () => {
    it('calls API and adds rubric to store', async () => {
      const request: CreateRubricRequest = {
        name: 'New Rubric',
        dimensions: [{ name: 'quality', weight: 1.0, description: 'Quality check' }],
      };
      const created = makeRubric({ id: 'r-new', name: 'New Rubric' });
      mockedApi.createRubric.mockResolvedValue(created);

      const result = await useRubricStore.getState().createRubric(request);

      expect(result).toEqual(created);
      expect(useRubricStore.getState().rubrics).toContainEqual(created);
      expect(mockedApi.createRubric).toHaveBeenCalledWith(request);
    });

    it('throws on API error', async () => {
      mockedApi.createRubric.mockRejectedValue(new Error('Create failed'));

      await expect(
        useRubricStore.getState().createRubric({
          name: 'Bad',
          dimensions: [{ name: 'x', weight: 1, description: '' }],
        }),
      ).rejects.toThrow('Create failed');
    });
  });

  describe('updateRubric', () => {
    it('calls API and updates rubric in store', async () => {
      const existing = makeRubric({ id: 'r-1', name: 'Old Name' });
      useRubricStore.setState({ rubrics: [existing] });

      const updated = makeRubric({ id: 'r-1', name: 'New Name' });
      mockedApi.updateRubric.mockResolvedValue(updated);

      const result = await useRubricStore.getState().updateRubric('r-1', { name: 'New Name' });

      expect(result).toEqual(updated);
      const rubrics = useRubricStore.getState().rubrics;
      expect(rubrics).toHaveLength(1);
      expect(rubrics[0]!.name).toBe('New Name');
      expect(mockedApi.updateRubric).toHaveBeenCalledWith('r-1', { name: 'New Name' });
    });
  });

  describe('deleteRubric', () => {
    it('calls API and removes rubric from store', async () => {
      const rubric = makeRubric({ id: 'r-1' });
      useRubricStore.setState({ rubrics: [rubric] });
      mockedApi.deleteRubric.mockResolvedValue(undefined);

      await useRubricStore.getState().deleteRubric('r-1');

      expect(useRubricStore.getState().rubrics).toEqual([]);
      expect(mockedApi.deleteRubric).toHaveBeenCalledWith('r-1');
    });
  });

  describe('importRubric', () => {
    it('calls API and adds imported rubric to store', async () => {
      const imported = makeRubric({ id: 'r-imported', name: 'Imported Rubric' });
      mockedApi.importRubric.mockResolvedValue(imported);

      const result = await useRubricStore.getState().importRubric({
        yaml_content: 'name: Imported Rubric\ndimensions: []',
      });

      expect(result).toEqual(imported);
      expect(useRubricStore.getState().rubrics).toContainEqual(imported);
      expect(mockedApi.importRubric).toHaveBeenCalledWith({
        yaml_content: 'name: Imported Rubric\ndimensions: []',
      });
    });

    it('throws on API error', async () => {
      mockedApi.importRubric.mockRejectedValue(new Error('Invalid YAML'));

      await expect(useRubricStore.getState().importRubric({ yaml_content: 'bad' })).rejects.toThrow(
        'Invalid YAML',
      );
    });
  });

  describe('generateRubric', () => {
    it('calls API and adds generated rubric to store', async () => {
      const generated = makeRubric({ id: 'r-gen', name: 'Generated Rubric' });
      mockedApi.generateRubric.mockResolvedValue(generated);

      const result = await useRubricStore.getState().generateRubric({
        description: 'Evaluate accuracy',
        provider_id: 'openai-gpt4',
      });

      expect(result).toEqual(generated);
      expect(useRubricStore.getState().rubrics).toContainEqual(generated);
      expect(mockedApi.generateRubric).toHaveBeenCalledWith({
        description: 'Evaluate accuracy',
        provider_id: 'openai-gpt4',
      });
    });

    it('passes sample_data when provided', async () => {
      const generated = makeRubric({ id: 'r-gen' });
      mockedApi.generateRubric.mockResolvedValue(generated);

      await useRubricStore.getState().generateRubric({
        description: 'Test',
        sample_data: 'Q: What? A: This.',
        provider_id: 'p1',
      });

      expect(mockedApi.generateRubric).toHaveBeenCalledWith({
        description: 'Test',
        sample_data: 'Q: What? A: This.',
        provider_id: 'p1',
      });
    });
  });

  describe('refineRubric', () => {
    it('calls API and updates refined rubric in store', async () => {
      const existing = makeRubric({ id: 'r-1', name: 'Old Rubric' });
      useRubricStore.setState({ rubrics: [existing] });

      const refined = makeRubric({
        id: 'r-1',
        name: 'Old Rubric',
        dimensions: [
          { name: 'accuracy', weight: 0.5, description: 'Accuracy' },
          { name: 'clarity', weight: 0.5, description: 'Clarity' },
        ],
      });
      mockedApi.refineRubric.mockResolvedValue(refined);

      const result = await useRubricStore.getState().refineRubric('r-1', {
        feedback: 'Add clarity dimension',
        provider_id: 'openai-gpt4',
      });

      expect(result).toEqual(refined);
      const rubrics = useRubricStore.getState().rubrics;
      expect(rubrics).toHaveLength(1);
      expect(rubrics[0]!.dimensions).toHaveLength(2);
      expect(mockedApi.refineRubric).toHaveBeenCalledWith('r-1', {
        feedback: 'Add clarity dimension',
        provider_id: 'openai-gpt4',
      });
    });
  });
});
