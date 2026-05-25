import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { DatasetDetail } from '@/types';

const mockFetchDataset = vi.fn();
const mockSetCurrentDataset = vi.fn();

const makeDetail = (overrides: Partial<DatasetDetail> = {}): DatasetDetail => ({
  id: 'ds-1',
  name: 'Test Dataset',
  description: 'A test dataset',
  format: 'qa_pairs',
  version: '1.0',
  tags: ['test', 'qa'],
  source_type: 'upload',
  item_count: 2,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  items: [
    {
      id: 'item-1',
      question: 'What is Linux?',
      expected_answer: 'An operating system kernel',
      metadata: {},
    },
    {
      id: 'item-2',
      question: 'What is Bash?',
      expected_answer: 'A Unix shell',
      metadata: {},
    },
  ],
  ...overrides,
});

let storeState: {
  currentDataset: DatasetDetail | null;
  isLoading: boolean;
  fetchDataset: typeof mockFetchDataset;
  setCurrentDataset: typeof mockSetCurrentDataset;
};

vi.mock('@/stores/datasetStore', () => ({
  useDatasetStore: (selector?: unknown) => {
    if (typeof selector === 'function') {
      return (selector as (s: typeof storeState) => unknown)(storeState);
    }
    return storeState;
  },
}));

import { DatasetDetailView } from './DatasetDetailView';

describe('DatasetDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState = {
      currentDataset: null,
      isLoading: false,
      fetchDataset: mockFetchDataset,
      setCurrentDataset: mockSetCurrentDataset,
    };
  });

  it('renders sheet when open with dataset name', () => {
    storeState.currentDataset = makeDetail();
    render(
      <DatasetDetailView datasetId="ds-1" open={true} onOpenChange={vi.fn()} />,
    );
    expect(screen.getByText('Test Dataset')).toBeInTheDocument();
  });

  it('calls fetchDataset with the provided id', () => {
    render(
      <DatasetDetailView datasetId="ds-1" open={true} onOpenChange={vi.fn()} />,
    );
    expect(mockFetchDataset).toHaveBeenCalledWith('ds-1');
  });

  it('displays dataset metadata fields', () => {
    storeState.currentDataset = makeDetail();
    render(
      <DatasetDetailView datasetId="ds-1" open={true} onOpenChange={vi.fn()} />,
    );
    expect(screen.getByText('qa_pairs')).toBeInTheDocument();
    expect(screen.getByText('1.0')).toBeInTheDocument();
  });

  it('renders item list when dataset has items', () => {
    storeState.currentDataset = makeDetail();
    render(
      <DatasetDetailView datasetId="ds-1" open={true} onOpenChange={vi.fn()} />,
    );
    expect(screen.getByText('What is Linux?')).toBeInTheDocument();
    expect(screen.getByText('An operating system kernel')).toBeInTheDocument();
    expect(screen.getByText('What is Bash?')).toBeInTheDocument();
  });

  it('shows loading state while fetching', () => {
    storeState.isLoading = true;
    render(
      <DatasetDetailView datasetId="ds-1" open={true} onOpenChange={vi.fn()} />,
    );
    expect(screen.getByTestId('detail-loading')).toBeInTheDocument();
  });
});
