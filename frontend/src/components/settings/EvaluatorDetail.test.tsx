import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { EvaluatorInfo } from '@/types';

const mockListConfigFiles = vi.fn();
const mockUploadConfigFile = vi.fn();
const mockDeleteConfigFile = vi.fn();
const mockGetConfigFile = vi.fn();

vi.mock('@/services/api', () => ({
  api: {
    listEvaluatorConfigFiles: (...args: unknown[]) => mockListConfigFiles(...args),
    uploadEvaluatorConfigFile: (...args: unknown[]) => mockUploadConfigFile(...args),
    deleteEvaluatorConfigFile: (...args: unknown[]) => mockDeleteConfigFile(...args),
    getEvaluatorConfigFile: (...args: unknown[]) => mockGetConfigFile(...args),
  },
}));

import { EvaluatorDetail } from './EvaluatorDetail';

const makeEvaluator = (overrides: Partial<EvaluatorInfo> = {}): EvaluatorInfo => ({
  id: 'litellm-judge',
  name: 'LLM-as-Judge',
  description: 'Direct LLM-as-judge scoring via LiteLLM.',
  modes: ['qa', 'rag', 'agent'],
  builtin: true,
  available: true,
  defaults: { pass_threshold: 0.7, temperature: 0.0 },
  config_schema: {
    type: 'object',
    properties: {
      model: { type: 'string', description: 'The model to use for judging.' },
      temperature: {
        type: 'number',
        description: 'Sampling temperature.',
        default: 0.0,
      },
    },
  },
  ...overrides,
});

describe('EvaluatorDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListConfigFiles.mockResolvedValue([]);
  });

  it('renders evaluator name and description', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    expect(screen.getByText('LLM-as-Judge')).toBeInTheDocument();
    expect(screen.getByText('Direct LLM-as-judge scoring via LiteLLM.')).toBeInTheDocument();
  });

  it('renders mode badges', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    expect(screen.getByText('qa')).toBeInTheDocument();
    expect(screen.getByText('rag')).toBeInTheDocument();
    expect(screen.getByText('agent')).toBeInTheDocument();
  });

  it('renders built-in badge for builtin evaluators', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator({ builtin: true })}
      />
    );

    expect(screen.getByText('Built-in')).toBeInTheDocument();
  });

  it('renders default configuration key-value pairs', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    expect(screen.getByText('pass_threshold')).toBeInTheDocument();
    expect(screen.getByText('0.7')).toBeInTheDocument();
    // "temperature" appears in both defaults and schema, so use getAllByText
    const temperatureElements = screen.getAllByText('temperature');
    expect(temperatureElements.length).toBeGreaterThanOrEqual(1);
  });

  it('shows "No default configuration" when defaults are empty', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator({ defaults: {} })}
      />
    );

    expect(screen.getByText('No default configuration')).toBeInTheDocument();
  });

  it('renders config schema properties', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    expect(screen.getByText('model')).toBeInTheDocument();
    expect(screen.getByText('string')).toBeInTheDocument();
    expect(screen.getByText('The model to use for judging.')).toBeInTheDocument();
  });

  it('shows "No configurable options" when config_schema is empty', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator({ config_schema: {} })}
      />
    );

    expect(screen.getByText('No configurable options')).toBeInTheDocument();
  });

  it('fetches config files on mount', () => {
    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    expect(mockListConfigFiles).toHaveBeenCalledWith('litellm-judge');
  });

  it('renders config file list', async () => {
    mockListConfigFiles.mockResolvedValue([
      { filename: 'rubric.yaml', size: 128, modified_at: '2026-01-01T00:00:00Z' },
      { filename: 'prompt.txt', size: 64, modified_at: '2026-01-02T00:00:00Z' },
    ]);

    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('rubric.yaml')).toBeInTheDocument();
      expect(screen.getByText('prompt.txt')).toBeInTheDocument();
    });
  });

  it('shows empty state when no config files', async () => {
    mockListConfigFiles.mockResolvedValue([]);

    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No config files uploaded')).toBeInTheDocument();
    });
  });

  it('can upload a config file', async () => {
    const user = userEvent.setup();
    mockUploadConfigFile.mockResolvedValue({ filename: 'test.yaml', size: 10 });
    mockListConfigFiles.mockResolvedValueOnce([]).mockResolvedValueOnce([
      { filename: 'test.yaml', size: 10, modified_at: '2026-01-01T00:00:00Z' },
    ]);

    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    const fileInput = screen.getByTestId('config-file-input');
    const file = new File(['content'], 'test.yaml', { type: 'text/yaml' });
    await user.upload(fileInput, file);

    const uploadButton = screen.getByRole('button', { name: /upload/i });
    await user.click(uploadButton);

    await waitFor(() => {
      expect(mockUploadConfigFile).toHaveBeenCalledWith('litellm-judge', file);
    });
  });

  it('can delete a config file', async () => {
    const user = userEvent.setup();
    mockListConfigFiles.mockResolvedValue([
      { filename: 'to-delete.yaml', size: 10, modified_at: '2026-01-01T00:00:00Z' },
    ]);
    mockDeleteConfigFile.mockResolvedValue(undefined);

    render(
      <EvaluatorDetail
        open={true}
        onOpenChange={vi.fn()}
        evaluator={makeEvaluator()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('to-delete.yaml')).toBeInTheDocument();
    });

    const deleteButton = screen.getByRole('button', { name: /delete/i });
    await user.click(deleteButton);

    // Confirm deletion
    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockDeleteConfigFile).toHaveBeenCalledWith('litellm-judge', 'to-delete.yaml');
    });
  });
});
