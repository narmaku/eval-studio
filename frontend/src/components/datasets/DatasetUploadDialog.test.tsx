import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockUploadDataset = vi.fn();
const mockOnOpenChange = vi.fn();

const defaultStoreState = {
  datasets: [],
  currentDataset: null,
  isLoading: false,
  error: null,
  fetchDatasets: vi.fn(),
  fetchDataset: vi.fn(),
  uploadDataset: mockUploadDataset,
  removeDataset: vi.fn(),
  setDatasets: vi.fn(),
  setCurrentDataset: vi.fn(),
  setLoading: vi.fn(),
  setError: vi.fn(),
  clearError: vi.fn(),
};

vi.mock('@/stores/datasetStore', () => ({
  useDatasetStore: (selector?: unknown) => {
    if (typeof selector === 'function') {
      return (selector as (s: typeof defaultStoreState) => unknown)(defaultStoreState);
    }
    return defaultStoreState;
  },
}));

import { DatasetUploadDialog } from './DatasetUploadDialog';

describe('DatasetUploadDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUploadDataset.mockResolvedValue({
      id: 'ds-new',
      name: 'Test',
      format: 'qa_pairs',
      item_count: 1,
    });
  });

  it('renders dialog when open', () => {
    render(<DatasetUploadDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByText('Upload Dataset')).toBeInTheDocument();
  });

  it('shows form fields', () => {
    render(<DatasetUploadDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByText(/format/i)).toBeInTheDocument();
  });

  it('submit button is disabled when form is empty', () => {
    render(<DatasetUploadDialog open={true} onOpenChange={mockOnOpenChange} />);
    const submitButton = screen.getByRole('button', { name: /upload/i });
    expect(submitButton).toBeDisabled();
  });

  it('calls uploadDataset on valid submission', async () => {
    const user = userEvent.setup();
    render(<DatasetUploadDialog open={true} onOpenChange={mockOnOpenChange} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'My Dataset');

    // Create a YAML file and attach it
    const yamlContent = `items:\n  - question: "What is Linux?"\n    expected_answer: "An OS kernel"`;
    const file = new File([yamlContent], 'test.yaml', { type: 'application/x-yaml' });
    const fileInput = screen.getByTestId('file-input');
    await user.upload(fileInput, file);

    // Wait for file to be parsed
    await waitFor(() => {
      expect(screen.getByText(/parsed 1 item/i)).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /upload/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockUploadDataset).toHaveBeenCalledTimes(1);
    });
  });

  it('closes dialog on successful upload', async () => {
    const user = userEvent.setup();
    render(<DatasetUploadDialog open={true} onOpenChange={mockOnOpenChange} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'My Dataset');

    const yamlContent = `items:\n  - question: "What is Linux?"\n    expected_answer: "An OS kernel"`;
    const file = new File([yamlContent], 'test.yaml', { type: 'application/x-yaml' });
    const fileInput = screen.getByTestId('file-input');
    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(screen.getByText(/parsed 1 item/i)).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /upload/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
