import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Dataset } from '@/types';

const mockFetchDatasets = vi.fn();
const mockRemoveDataset = vi.fn();

const defaultStoreState = {
  datasets: [] as Dataset[],
  currentDataset: null,
  isLoading: false,
  error: null,
  fetchDatasets: mockFetchDatasets,
  fetchDataset: vi.fn(),
  uploadDataset: vi.fn(),
  removeDataset: mockRemoveDataset,
  setDatasets: vi.fn(),
  setCurrentDataset: vi.fn(),
  setLoading: vi.fn(),
  setError: vi.fn(),
  clearError: vi.fn(),
};

let storeState = { ...defaultStoreState };

vi.mock('@/stores/datasetStore', () => ({
  useDatasetStore: (selector?: unknown) => {
    if (typeof selector === 'function') {
      return (selector as (s: typeof storeState) => unknown)(storeState);
    }
    return storeState;
  },
}));

// Stub child components to avoid testing them here
vi.mock('@/components/datasets/DatasetUploadDialog', () => ({
  DatasetUploadDialog: () => <div data-testid="upload-dialog" />,
}));

vi.mock('@/components/datasets/DatasetDetailView', () => ({
  DatasetDetailView: () => <div data-testid="detail-view" />,
}));

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

describe('Datasets page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState = { ...defaultStoreState };
  });

  // Lazy-import the component after mocks are set up
  async function renderPage() {
    const mod = await import('./Datasets');
    const Datasets = mod.default;
    return render(<Datasets />);
  }

  it('renders page heading', async () => {
    await renderPage();
    expect(screen.getByRole('heading', { name: 'Datasets' })).toBeInTheDocument();
  });

  it('calls fetchDatasets on mount', async () => {
    await renderPage();
    expect(mockFetchDatasets).toHaveBeenCalledTimes(1);
  });

  it('shows loading spinner while fetching', async () => {
    storeState = { ...defaultStoreState, isLoading: true };
    await renderPage();
    expect(screen.getByTestId('datasets-loading')).toBeInTheDocument();
  });

  it('shows empty state when no datasets', async () => {
    storeState = { ...defaultStoreState, datasets: [], isLoading: false };
    await renderPage();
    expect(screen.getByText('No datasets yet')).toBeInTheDocument();
  });

  it('renders table with dataset rows', async () => {
    storeState = {
      ...defaultStoreState,
      datasets: [
        makeDataset({ id: 'ds-1', name: 'Dataset One' }),
        makeDataset({ id: 'ds-2', name: 'Dataset Two' }),
      ],
    };
    await renderPage();
    expect(screen.getByText('Dataset One')).toBeInTheDocument();
    expect(screen.getByText('Dataset Two')).toBeInTheDocument();
  });

  it('renders Upload Dataset button', async () => {
    await renderPage();
    const buttons = screen.getAllByRole('button', { name: /upload dataset/i });
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });
});
