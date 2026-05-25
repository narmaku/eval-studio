import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DatasetSelector } from './DatasetSelector';
import { useDatasetStore } from '@/stores/datasetStore';
import type { Dataset } from '@/types';

const mockDatasets: Dataset[] = [
  {
    id: 'ds-1',
    name: 'RHEL Sysadmin Q&A',
    description: 'Linux admin questions',
    format: 'qa_pairs',
    version: '1.0',
    tags: [],
    source: { type: 'upload', original_format: 'yaml', imported_at: '2024-01-01T00:00:00Z' },
    stats: { item_count: 50, categories: [], avg_question_length: 100, avg_answer_length: 200 },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'ds-2',
    name: 'Kubernetes Basics',
    description: 'K8s fundamentals',
    format: 'qa_pairs',
    version: '1.0',
    tags: [],
    source: { type: 'upload', original_format: 'yaml', imported_at: '2024-01-01T00:00:00Z' },
    stats: { item_count: 30, categories: [], avg_question_length: 80, avg_answer_length: 150 },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'ds-3',
    name: 'Networking',
    description: 'Network troubleshooting',
    format: 'qa_pairs',
    version: '1.0',
    tags: [],
    source: { type: 'upload', original_format: 'csv', imported_at: '2024-01-01T00:00:00Z' },
    stats: { item_count: 20, categories: [], avg_question_length: 90, avg_answer_length: 120 },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

// Mock the API module so fetchDatasets does not make real HTTP calls.
// vi.mock is hoisted, so we cannot reference mockDatasets here -- use a
// factory that returns the data inline.
vi.mock('@/services/api', () => ({
  api: {
    listDatasets: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'ds-1',
          name: 'RHEL Sysadmin Q&A',
          description: 'Linux admin questions',
          format: 'qa_pairs',
          version: '1.0',
          tags: [],
          source: { type: 'upload', original_format: 'yaml', imported_at: '2024-01-01T00:00:00Z' },
          stats: { item_count: 50, categories: [], avg_question_length: 100, avg_answer_length: 200 },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        {
          id: 'ds-2',
          name: 'Kubernetes Basics',
          description: 'K8s fundamentals',
          format: 'qa_pairs',
          version: '1.0',
          tags: [],
          source: { type: 'upload', original_format: 'yaml', imported_at: '2024-01-01T00:00:00Z' },
          stats: { item_count: 30, categories: [], avg_question_length: 80, avg_answer_length: 150 },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        {
          id: 'ds-3',
          name: 'Networking',
          description: 'Network troubleshooting',
          format: 'qa_pairs',
          version: '1.0',
          tags: [],
          source: { type: 'upload', original_format: 'csv', imported_at: '2024-01-01T00:00:00Z' },
          stats: { item_count: 20, categories: [], avg_question_length: 90, avg_answer_length: 120 },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 3,
      page: 1,
      page_size: 10,
      pages: 1,
    }),
  },
}));

describe('DatasetSelector', () => {
  beforeEach(() => {
    // Reset store to a clean initial state before each test.
    // The component will call fetchDatasets on mount, which will populate
    // datasets from the mocked API response.
    useDatasetStore.setState({
      datasets: [],
      isLoading: false,
      error: null,
    });
  });

  it('renders the select trigger', () => {
    const onChange = vi.fn();
    render(<DatasetSelector value={undefined} onChange={onChange} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toBeInTheDocument();
  });

  it('shows placeholder text after datasets are loaded', async () => {
    const onChange = vi.fn();
    render(<DatasetSelector value={undefined} onChange={onChange} />);

    // After the mocked fetchDatasets resolves, the placeholder should show
    await waitFor(() => {
      expect(screen.getByText('Select a dataset...')).toBeInTheDocument();
    });
  });

  it('shows loading placeholder while fetching', () => {
    // Override fetchDatasets with a function that just sets loading and never resolves
    const neverResolve = () => {
      useDatasetStore.setState({ isLoading: true });
      return new Promise<void>(() => {});
    };
    useDatasetStore.setState({ isLoading: true, datasets: [], fetchDatasets: neverResolve });

    const onChange = vi.fn();
    render(<DatasetSelector value={undefined} onChange={onChange} />);

    expect(screen.getByText('Loading datasets...')).toBeInTheDocument();
  });

  it('disables the trigger when store is loading', () => {
    const neverResolve = () => {
      useDatasetStore.setState({ isLoading: true });
      return new Promise<void>(() => {});
    };
    useDatasetStore.setState({ isLoading: true, datasets: [], fetchDatasets: neverResolve });

    const onChange = vi.fn();
    render(<DatasetSelector value={undefined} onChange={onChange} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).toBeDisabled();
  });

  it('disables the trigger when disabled prop is true', async () => {
    const onChange = vi.fn();
    render(<DatasetSelector value={undefined} onChange={onChange} disabled />);

    await waitFor(() => {
      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeDisabled();
    });
  });

  it('trigger is not disabled when datasets are pre-loaded and not loading', () => {
    // Pre-populate the store with datasets and not loading
    useDatasetStore.setState({
      datasets: mockDatasets,
      isLoading: false,
      // Override fetchDatasets to not trigger loading state
      fetchDatasets: vi.fn().mockResolvedValue(undefined),
    });

    const onChange = vi.fn();
    render(<DatasetSelector value={undefined} onChange={onChange} />);

    const trigger = screen.getByRole('combobox');
    expect(trigger).not.toBeDisabled();
  });
});
