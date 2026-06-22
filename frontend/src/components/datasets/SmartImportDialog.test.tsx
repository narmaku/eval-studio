import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import type { AnalyzeResponse } from '@/types';

const mockAnalyzeFiles = vi.fn();
const mockSmartImport = vi.fn();
const mockClearAnalysis = vi.fn();
const mockFetchDatasets = vi.fn();
const mockOnOpenChange = vi.fn();

const makeAnalysisResult = (overrides: Partial<AnalyzeResponse> = {}): AnalyzeResponse => ({
  analysis_id: 'analysis-1',
  files: [
    {
      filename: 'test.yaml',
      format: 'yaml',
      total_rows: 10,
      has_header: true,
      nested_paths: [],
      fields: ['question', 'expected_answer', 'category'],
      sample_rows: [
        { question: 'What is Linux?', expected_answer: 'An OS kernel', category: 'basics' },
        { question: 'What is bash?', expected_answer: 'A shell', category: 'tools' },
      ],
      error: null,
    },
  ],
  merged_fields: ['question', 'expected_answer', 'category'],
  suggested_mapping: {
    question_field: 'question',
    answer_field: 'expected_answer',
    metadata_fields: ['category'],
    confidence: 0.95,
  },
  total_items: 10,
  ...overrides,
});

let storeState: Record<string, unknown>;

const defaultStoreState = {
  datasets: [],
  currentDataset: null,
  isLoading: false,
  error: null,
  analysisResult: null as AnalyzeResponse | null,
  isAnalyzing: false,
  isImporting: false,
  fetchDatasets: mockFetchDatasets,
  fetchDataset: vi.fn(),
  uploadDataset: vi.fn(),
  removeDataset: vi.fn(),
  setDatasets: vi.fn(),
  setCurrentDataset: vi.fn(),
  setLoading: vi.fn(),
  setError: vi.fn(),
  clearError: vi.fn(),
  analyzeFiles: mockAnalyzeFiles,
  smartImport: mockSmartImport,
  clearAnalysis: mockClearAnalysis,
};

vi.mock('@/stores/datasetStore', () => ({
  useDatasetStore: (selector?: unknown) => {
    if (typeof selector === 'function') {
      return (selector as (s: typeof storeState) => unknown)(storeState);
    }
    return storeState;
  },
}));

// Dynamically import after mocks
import { SmartImportDialog } from './SmartImportDialog';

describe('SmartImportDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState = { ...defaultStoreState };
    mockAnalyzeFiles.mockResolvedValue(undefined);
    mockSmartImport.mockResolvedValue({
      id: 'ds-new',
      name: 'Test',
      format: 'qa_pairs',
      item_count: 10,
    });
  });

  it('renders upload step when open', () => {
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByText('Import Dataset')).toBeInTheDocument();
    expect(screen.getByText(/drop files here/i)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<SmartImportDialog open={false} onOpenChange={mockOnOpenChange} />);
    expect(screen.queryByText('Import Dataset')).not.toBeInTheDocument();
  });

  it('shows step indicator', () => {
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByTestId('step-indicator')).toBeInTheDocument();
  });

  it('renders directory upload button', () => {
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByTestId('dir-upload-button')).toBeInTheDocument();
    expect(screen.getByText('Upload Directory')).toBeInTheDocument();
  });

  it('shows file list after files selected', async () => {
    const user = userEvent.setup();
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);

    expect(screen.getByTestId('file-list')).toBeInTheDocument();
    expect(screen.getByText('test.yaml')).toBeInTheDocument();
  });

  it('allows removing a file from the list', async () => {
    const user = userEvent.setup();
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);

    expect(screen.getByText('test.yaml')).toBeInTheDocument();

    const removeBtn = screen.getByLabelText('Remove test.yaml');
    await user.click(removeBtn);

    expect(screen.queryByText('test.yaml')).not.toBeInTheDocument();
  });

  it('analyze button is disabled when no files selected', () => {
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);
    const analyzeBtn = screen.getByTestId('analyze-button');
    expect(analyzeBtn).toBeDisabled();
  });

  it('analyze button is enabled when files are selected', async () => {
    const user = userEvent.setup();
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);

    const analyzeBtn = screen.getByTestId('analyze-button');
    expect(analyzeBtn).not.toBeDisabled();
  });

  it('calls analyzeFiles when analyze button clicked', async () => {
    const user = userEvent.setup();
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);

    const analyzeBtn = screen.getByTestId('analyze-button');
    await user.click(analyzeBtn);

    expect(mockAnalyzeFiles).toHaveBeenCalledTimes(1);
    expect(mockAnalyzeFiles).toHaveBeenCalledWith([file]);
  });

  it('shows analysis results after analyze (step 2)', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    // Mock analyzeFiles to trigger step change
    mockAnalyzeFiles.mockResolvedValue(undefined);

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Upload file and click analyze
    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);

    const analyzeBtn = screen.getByTestId('analyze-button');
    await user.click(analyzeBtn);

    // After analysis, rerender with analysis result (simulating store update)
    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByText('Map Fields')).toBeInTheDocument();
    });

    // Check file summary
    expect(screen.getByText('test.yaml')).toBeInTheDocument();
    expect(screen.getByText('yaml')).toBeInTheDocument();
    expect(screen.getByText('10 rows')).toBeInTheDocument();
  });

  it('pre-populates mapping from suggestion', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Navigate to step 2
    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByText('Map Fields')).toBeInTheDocument();
    });

    // The mapping selects should show the pre-populated values
    const questionSelect = screen.getByTestId('question-field-select');
    expect(questionSelect).toBeInTheDocument();
  });

  it('shows confidence indicator', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByTestId('confidence-badge')).toBeInTheDocument();
    });
    expect(screen.getByText(/high/i)).toBeInTheDocument();
    expect(screen.getByText(/95%/)).toBeInTheDocument();
  });

  it('shows merge mode selector', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByTestId('merge-mode-select')).toBeInTheDocument();
    });
  });

  it('shows detected fields as badges', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByText('Detected Fields')).toBeInTheDocument();
    });
  });

  it('navigates back to previous step', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Go to step 2
    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByText('Map Fields')).toBeInTheDocument();
    });

    // Click back
    const backBtn = screen.getByTestId('back-button');
    await user.click(backBtn);

    expect(screen.getByText('Import Dataset')).toBeInTheDocument();
  });

  it('shows preview table with mapped data on step 3', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Navigate to step 2
    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByText('Map Fields')).toBeInTheDocument();
    });

    // Navigate to step 3
    const nextBtn = screen.getByTestId('next-button');
    await user.click(nextBtn);

    expect(screen.getByText('Preview & Confirm')).toBeInTheDocument();
    // Preview table should show sample data
    expect(screen.getByText('What is Linux?')).toBeInTheDocument();
    expect(screen.getByText('An OS kernel')).toBeInTheDocument();
  });

  it('disables import when name is empty', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Navigate to step 2
    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByTestId('next-button')).toBeInTheDocument();
    });

    // Navigate to step 3
    await user.click(screen.getByTestId('next-button'));

    // Clear the name field (pre-populated from filename)
    const nameInput = screen.getByTestId('dataset-name-input') as HTMLInputElement;
    await user.clear(nameInput);

    await waitFor(() => {
      expect(nameInput).toHaveValue('');
    });

    const importBtn = screen.getByTestId('import-button');
    expect(importBtn).toBeDisabled();
  });

  it('calls smartImport on confirm', async () => {
    const analysisResult = makeAnalysisResult();
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Navigate through steps
    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByTestId('next-button')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('next-button'));

    // Name should be pre-populated from file name
    const importBtn = screen.getByTestId('import-button');
    await user.click(importBtn);

    await waitFor(() => {
      expect(mockSmartImport).toHaveBeenCalledTimes(1);
      expect(mockSmartImport).toHaveBeenCalledWith(
        expect.objectContaining({
          analysis_id: 'analysis-1',
          name: 'test',
          mapping: {
            question_field: 'question',
            answer_field: 'expected_answer',
          },
          merge_mode: 'single',
        }),
      );
    });
  });

  it('closes dialog and calls clearAnalysis on cancel', async () => {
    storeState = {
      ...defaultStoreState,
      analysisResult: makeAnalysisResult(),
    };

    const user = userEvent.setup();
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const cancelBtn = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelBtn);

    expect(mockClearAnalysis).toHaveBeenCalled();
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('resets state on close', () => {
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Close the dialog
    rerender(<SmartImportDialog open={false} onOpenChange={mockOnOpenChange} />);

    // Reopen - should be back to step 1
    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    expect(screen.getByText('Import Dataset')).toBeInTheDocument();
  });

  it('shows file errors from analysis', async () => {
    const analysisResult = makeAnalysisResult({
      files: [
        {
          filename: 'bad.csv',
          format: 'csv',
          total_rows: 0,
          has_header: true,
          nested_paths: [],
          fields: [],
          sample_rows: [],
          error: 'Invalid CSV format',
        },
      ],
    });
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'bad.csv', { type: 'text/csv' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByText('Invalid CSV format')).toBeInTheDocument();
    });
  });

  it('filters out unsupported file extensions', async () => {
    const user = userEvent.setup();
    render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    // Try to upload a .txt file
    const txtFile = new File(['content'], 'test.txt', { type: 'text/plain' });
    const yamlFile = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');

    await user.upload(input, [txtFile, yamlFile]);

    // Only the yaml file should appear
    await waitFor(() => {
      expect(screen.getByText('test.yaml')).toBeInTheDocument();
      expect(screen.queryByText('test.txt')).not.toBeInTheDocument();
    });
  });

  it('shows low confidence indicator for low confidence mapping', async () => {
    const analysisResult = makeAnalysisResult({
      suggested_mapping: {
        question_field: 'question',
        answer_field: 'expected_answer',
        metadata_fields: ['category'],
        confidence: 0.3,
      },
    });
    storeState = { ...defaultStoreState, analysisResult };

    const user = userEvent.setup();
    const { rerender } = render(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    const file = new File(['content'], 'test.yaml', { type: 'application/x-yaml' });
    const input = screen.getByTestId('file-input');
    await user.upload(input, file);
    await user.click(screen.getByTestId('analyze-button'));

    rerender(<SmartImportDialog open={true} onOpenChange={mockOnOpenChange} />);

    await waitFor(() => {
      expect(screen.getByText(/low/i)).toBeInTheDocument();
    });
  });
});
