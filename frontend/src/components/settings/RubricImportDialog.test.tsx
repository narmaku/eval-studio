import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import type { RubricAnalyzeResponse } from '@/types';

const mockImportRubric = vi.fn();
const mockAnalyzeRubric = vi.fn();
const mockClearAnalysis = vi.fn();

let mockAnalyzeResult: RubricAnalyzeResponse | null = null;
let mockIsAnalyzing = false;

vi.mock('@/stores/rubricStore', () => {
  const getState = () => ({
    importRubric: mockImportRubric,
    analyzeRubric: mockAnalyzeRubric,
    analyzeResult: mockAnalyzeResult,
    isAnalyzing: mockIsAnalyzing,
    clearAnalysis: mockClearAnalysis,
  });

  return {
    useRubricStore: Object.assign(
      (selector?: unknown) => {
        const state = getState();
        if (typeof selector === 'function') {
          return (selector as (s: typeof state) => unknown)(state);
        }
        return state;
      },
      { getState },
    ),
  };
});

import { RubricImportDialog } from './RubricImportDialog';

function makeSingleMetricAnalysis(
  overrides?: Partial<RubricAnalyzeResponse>,
): RubricAnalyzeResponse {
  return {
    detected_format: 'rubric_kit',
    metrics: [
      {
        metric_id: null,
        suggested_name: 'Test Rubric',
        suggested_description: 'A test rubric description',
        dimensions_preview: [
          {
            name: 'accuracy',
            description: 'How accurate the answer is',
            weight: 1.0,
            criteria_count: 3,
            criteria: [
              { name: 'factual', criterion: 'Is the answer factually correct?' },
              { name: 'precise', criterion: 'Is the answer precise?' },
              { name: 'sourced', criterion: 'Are claims properly sourced?' },
            ],
          },
          {
            name: 'clarity',
            description: 'How clear the answer is',
            weight: 0.5,
            criteria_count: 2,
            criteria: [
              { name: 'readable', criterion: 'Is it easy to read?' },
              { name: 'structured', criterion: 'Is it well structured?' },
            ],
          },
        ],
        criteria_count: 5,
        pass_threshold: 0.8,
      },
    ],
    ...overrides,
  };
}

function makeMultiMetricAnalysis(): RubricAnalyzeResponse {
  return {
    detected_format: 'ls_eval_system_config',
    metrics: [
      {
        metric_id: 'geval:metric_a',
        suggested_name: 'Metric A',
        suggested_description: 'First metric',
        dimensions_preview: [
          {
            name: 'dim_a1',
            description: 'Dimension A1',
            weight: 1.0,
            criteria_count: 2,
            criteria: [
              { name: 'c1', criterion: 'Check A' },
              { name: 'c2', criterion: 'Check B' },
            ],
          },
        ],
        criteria_count: 2,
        pass_threshold: 0.7,
      },
      {
        metric_id: 'geval:metric_b',
        suggested_name: 'Metric B',
        suggested_description: 'Second metric',
        dimensions_preview: [
          {
            name: 'dim_b1',
            description: 'Dimension B1',
            weight: 1.0,
            criteria_count: 4,
            criteria: [
              { name: 'c1', criterion: 'Check C' },
              { name: 'c2', criterion: 'Check D' },
              { name: 'c3', criterion: 'Check E' },
              { name: 'c4', criterion: 'Check F' },
            ],
          },
        ],
        criteria_count: 4,
        pass_threshold: 0.9,
      },
    ],
  };
}

describe('RubricImportDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAnalyzeResult = null;
    mockIsAnalyzing = false;
  });

  it('renders nothing when closed', () => {
    render(<RubricImportDialog open={false} onOpenChange={vi.fn()} />);
    expect(screen.queryByText(/import rubric/i)).not.toBeInTheDocument();
  });

  it('renders step 1 by default with upload and textarea', () => {
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);
    expect(screen.getByText('Import Rubric')).toBeInTheDocument();
    expect(screen.getByLabelText(/upload yaml file/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/paste yaml/i)).toBeInTheDocument();
    expect(screen.getByTestId('analyze-button')).toBeInTheDocument();
    expect(screen.getByText(/supports rubric-kit/i)).toBeInTheDocument();
  });

  it('shows step indicator with 2 dots', () => {
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);
    const indicator = screen.getByTestId('step-indicator');
    const dots = within(indicator).getAllByRole('presentation', { hidden: true });
    expect(dots).toHaveLength(2);
  });

  it('disables analyze button when textarea is empty', () => {
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);
    expect(screen.getByTestId('analyze-button')).toBeDisabled();
  });

  it('enables analyze button when yaml content is entered', async () => {
    const user = userEvent.setup();
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/paste yaml/i);
    await user.type(textarea, 'name: test');

    expect(screen.getByTestId('analyze-button')).not.toBeDisabled();
  });

  it('analyzes YAML and advances to step 2', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/paste yaml/i);
    await user.type(textarea, 'name: test');
    await user.click(screen.getByTestId('analyze-button'));

    expect(mockAnalyzeRubric).toHaveBeenCalledWith('name: test');

    // Re-render with updated analyzeResult
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByText('Preview & Confirm')).toBeInTheDocument();
  });

  it('shows detected format badge on step 2', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis({ detected_format: 'geval' });

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const badge = screen.getByTestId('format-badge');
    expect(badge).toHaveTextContent('geval');
  });

  it('pre-fills name from analyze response', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const nameInput = screen.getByTestId('rubric-name-input');
    expect(nameInput).toHaveValue('Test Rubric');
  });

  it('allows name override', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const nameInput = screen.getByTestId('rubric-name-input');
    await user.clear(nameInput);
    await user.type(nameInput, 'My Custom Name');
    expect(nameInput).toHaveValue('My Custom Name');
  });

  it('shows dimensions preview on step 2', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByText('accuracy')).toBeInTheDocument();
    expect(screen.getByText('clarity')).toBeInTheDocument();
    expect(screen.getByText(/5 criteria total/)).toBeInTheDocument();
  });

  it('shows metric selector for multiple metrics', async () => {
    const user = userEvent.setup();
    const analysis = makeMultiMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByTestId('metric-select')).toBeInTheDocument();
    expect(screen.getByText('Select Metric')).toBeInTheDocument();
  });

  it('does not show metric selector for single metric', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    expect(screen.queryByTestId('metric-select')).not.toBeInTheDocument();
  });

  it('imports with metadata fields', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });
    mockImportRubric.mockResolvedValue({ id: 'r-1', name: 'Test Rubric' });

    const onImported = vi.fn();
    const onOpenChange = vi.fn();
    const { rerender } = render(
      <RubricImportDialog open={true} onOpenChange={onOpenChange} onImported={onImported} />,
    );

    // Step 1: enter YAML and analyze
    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(
      <RubricImportDialog open={true} onOpenChange={onOpenChange} onImported={onImported} />,
    );

    // Step 2: fill metadata and import
    const descInput = screen.getByPlaceholderText(/optional description/i);
    await user.clear(descInput);
    await user.type(descInput, 'My custom description');

    const tagsInput = screen.getByPlaceholderText(/tag1, tag2/i);
    await user.type(tagsInput, 'quality, scoring');

    await user.click(screen.getByTestId('import-button'));

    expect(mockImportRubric).toHaveBeenCalledWith({
      yaml_content: 'name: test',
      name: 'Test Rubric',
      description: 'My custom description',
      tags: ['quality', 'scoring'],
      metric_id: undefined,
    });
    expect(onImported).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('back button returns to step 1', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    expect(screen.getByText('Preview & Confirm')).toBeInTheDocument();

    await user.click(screen.getByTestId('back-button'));

    expect(screen.getByText('Import Rubric')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/paste yaml/i)).toBeInTheDocument();
  });

  it('resets state on close', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const onOpenChange = vi.fn();
    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={onOpenChange} />);

    // Type content and analyze
    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={onOpenChange} />);

    // Click cancel
    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(mockClearAnalysis).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('shows error on analyze failure', async () => {
    const user = userEvent.setup();
    mockAnalyzeRubric.mockRejectedValue(new Error('Invalid YAML syntax'));

    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'bad yaml');
    await user.click(screen.getByTestId('analyze-button'));

    expect(await screen.findByText(/invalid yaml syntax/i)).toBeInTheDocument();
  });

  it('disables import button when name is empty', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    // Clear the pre-filled name
    const nameInput = screen.getByTestId('rubric-name-input');
    await user.clear(nameInput);

    expect(screen.getByTestId('import-button')).toBeDisabled();
  });

  it('shows error on import failure', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });
    mockImportRubric.mockRejectedValue(new Error('Server error'));

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.click(screen.getByTestId('import-button'));

    expect(await screen.findByText(/server error/i)).toBeInTheDocument();
  });

  it('populates textarea from file upload', async () => {
    const user = userEvent.setup();
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const fileInput = screen.getByLabelText(/upload yaml file/i);
    const file = new File(['name: from-file'], 'rubric.yaml', { type: 'application/x-yaml' });
    await user.upload(fileInput, file);

    // FileReader is async; wait for the analyze button to become enabled
    await vi.waitFor(() => {
      expect(screen.getByTestId('analyze-button')).not.toBeDisabled();
    });
  });

  it('shows analyzing spinner and disables button while analyzing', async () => {
    mockIsAnalyzing = true;
    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    // Even if there were content, analyzing state disables the button
    const analyzeButton = screen.getByTestId('analyze-button');
    expect(analyzeButton).toBeDisabled();
    expect(screen.getByText('Analyzing...')).toBeInTheDocument();
  });

  it('pre-fills description from analysis response', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const descInput = screen.getByPlaceholderText(/optional description/i);
    expect(descInput).toHaveValue('A test rubric description');
  });

  it('shows ls-eval system config format label', async () => {
    const user = userEvent.setup();
    const analysis = makeMultiMetricAnalysis(); // uses ls_eval_system_config

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    const badge = screen.getByTestId('format-badge');
    expect(badge).toHaveTextContent('ls-eval system config');
  });

  it('passes metric_id on import when metric has one', async () => {
    const user = userEvent.setup();
    const analysis = makeMultiMetricAnalysis(); // metrics have metric_id

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });
    mockImportRubric.mockResolvedValue({ id: 'r-1', name: 'Metric A' });

    const onImported = vi.fn();
    const onOpenChange = vi.fn();
    const { rerender } = render(
      <RubricImportDialog open={true} onOpenChange={onOpenChange} onImported={onImported} />,
    );

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(
      <RubricImportDialog open={true} onOpenChange={onOpenChange} onImported={onImported} />,
    );

    await user.click(screen.getByTestId('import-button'));

    expect(mockImportRubric).toHaveBeenCalledWith(
      expect.objectContaining({
        metric_id: 'geval:metric_a',
      }),
    );
  });

  it('shows fallback error message for non-Error thrown during analyze', async () => {
    const user = userEvent.setup();
    mockAnalyzeRubric.mockRejectedValue('string error');

    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'bad yaml');
    await user.click(screen.getByTestId('analyze-button'));

    expect(await screen.findByText(/analysis failed/i)).toBeInTheDocument();
  });

  it('shows fallback error message for non-Error thrown during import', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });
    mockImportRubric.mockRejectedValue(42);

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.click(screen.getByTestId('import-button'));

    expect(await screen.findByText(/import failed/i)).toBeInTheDocument();
  });

  it('clears error when typing new content in step 1', async () => {
    const user = userEvent.setup();
    mockAnalyzeRubric.mockRejectedValue(new Error('Parse error'));

    render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'bad');
    await user.click(screen.getByTestId('analyze-button'));

    expect(await screen.findByText(/parse error/i)).toBeInTheDocument();

    // Typing more content should clear the error
    await user.type(screen.getByPlaceholderText(/paste yaml/i), ' yaml');
    expect(screen.queryByText(/parse error/i)).not.toBeInTheDocument();
  });

  it('back button clears error from step 2', async () => {
    const user = userEvent.setup();
    const analysis = makeSingleMetricAnalysis();

    mockAnalyzeRubric.mockImplementation(async () => {
      mockAnalyzeResult = analysis;
    });
    mockImportRubric.mockRejectedValue(new Error('Import conflict'));

    const { rerender } = render(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText(/paste yaml/i), 'name: test');
    await user.click(screen.getByTestId('analyze-button'));
    rerender(<RubricImportDialog open={true} onOpenChange={vi.fn()} />);

    await user.click(screen.getByTestId('import-button'));
    expect(await screen.findByText(/import conflict/i)).toBeInTheDocument();

    await user.click(screen.getByTestId('back-button'));
    expect(screen.queryByText(/import conflict/i)).not.toBeInTheDocument();
  });
});
