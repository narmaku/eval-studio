import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RunDetailsPanel } from './RunDetailsPanel';
import {
  metadataEntriesToRecord,
  recordToMetadataEntries,
  buildAutoMetadata,
  buildRAGAutoMetadata,
  buildArenaAutoMetadata,
} from './runDetailsUtils';

describe('RunDetailsPanel', () => {
  const defaultProps = {
    title: 'Test Eval',
    onTitleChange: vi.fn(),
    description: '',
    onDescriptionChange: vi.fn(),
    metadata: [],
    onMetadataChange: vi.fn(),
  };

  it('renders collapsed by default with title', () => {
    render(<RunDetailsPanel {...defaultProps} />);
    expect(screen.getByText('Run Details')).toBeInTheDocument();
    // Title input should not be visible when collapsed
    expect(screen.queryByLabelText('Title')).not.toBeInTheDocument();
  });

  it('shows fields when expanded', () => {
    render(<RunDetailsPanel {...defaultProps} />);
    fireEvent.click(screen.getByText('Run Details'));
    expect(screen.getByLabelText('Title')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
  });

  it('shows active count badge when title is set', () => {
    render(<RunDetailsPanel {...defaultProps} title="My Eval" />);
    expect(screen.getByText('1 set')).toBeInTheDocument();
  });

  it('calls onTitleChange when title input changes', () => {
    const onTitleChange = vi.fn();
    render(<RunDetailsPanel {...defaultProps} onTitleChange={onTitleChange} />);
    fireEvent.click(screen.getByText('Run Details'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'New Title' } });
    expect(onTitleChange).toHaveBeenCalledWith('New Title');
  });

  it('calls onDescriptionChange when description changes', () => {
    const onDescriptionChange = vi.fn();
    render(<RunDetailsPanel {...defaultProps} onDescriptionChange={onDescriptionChange} />);
    fireEvent.click(screen.getByText('Run Details'));
    fireEvent.change(screen.getByLabelText('Description'), {
      target: { value: 'Some description' },
    });
    expect(onDescriptionChange).toHaveBeenCalledWith('Some description');
  });

  it('adds metadata entry when Add button is clicked', () => {
    const onMetadataChange = vi.fn();
    render(<RunDetailsPanel {...defaultProps} onMetadataChange={onMetadataChange} />);
    fireEvent.click(screen.getByText('Run Details'));
    fireEvent.click(screen.getByText('Add'));
    expect(onMetadataChange).toHaveBeenCalledWith([{ key: '', value: '' }]);
  });

  it('removes metadata entry when remove button is clicked', () => {
    const onMetadataChange = vi.fn();
    const metadata = [
      { key: 'provider', value: 'openai' },
      { key: 'model', value: 'gpt-4o' },
    ];
    render(
      <RunDetailsPanel {...defaultProps} metadata={metadata} onMetadataChange={onMetadataChange} />,
    );
    fireEvent.click(screen.getByText('Run Details'));
    const removeButtons = screen.getAllByLabelText(/Remove metadata entry/);
    fireEvent.click(removeButtons[0]!);
    expect(onMetadataChange).toHaveBeenCalledWith([{ key: 'model', value: 'gpt-4o' }]);
  });

  it('renders existing metadata entries', () => {
    const metadata = [
      { key: 'provider', value: 'openai' },
      { key: 'model', value: 'gpt-4o' },
    ];
    render(<RunDetailsPanel {...defaultProps} metadata={metadata} />);
    fireEvent.click(screen.getByText('Run Details'));
    expect(screen.getByDisplayValue('provider')).toBeInTheDocument();
    expect(screen.getByDisplayValue('openai')).toBeInTheDocument();
    expect(screen.getByDisplayValue('model')).toBeInTheDocument();
    expect(screen.getByDisplayValue('gpt-4o')).toBeInTheDocument();
  });

  it('shows correct active count with metadata entries', () => {
    const metadata = [
      { key: 'provider', value: 'openai' },
      { key: 'model', value: 'gpt-4o' },
    ];
    render(
      <RunDetailsPanel
        {...defaultProps}
        title="My Eval"
        description="A test"
        metadata={metadata}
      />,
    );
    // title (1) + description (1) + 2 metadata entries with keys = 4
    expect(screen.getByText('4 set')).toBeInTheDocument();
  });

  it('hides description and metadata when props are omitted', () => {
    render(<RunDetailsPanel title="Title Only" onTitleChange={vi.fn()} />);
    fireEvent.click(screen.getByText('Run Details'));
    expect(screen.getByLabelText('Title')).toBeInTheDocument();
    expect(screen.queryByLabelText('Description')).not.toBeInTheDocument();
    expect(screen.queryByText('Metadata')).not.toBeInTheDocument();
    expect(screen.queryByText('Add')).not.toBeInTheDocument();
  });

  it('counts only title for active badge when description/metadata omitted', () => {
    render(<RunDetailsPanel title="My Title" onTitleChange={vi.fn()} />);
    expect(screen.getByText('1 set')).toBeInTheDocument();
  });
});

describe('metadataEntriesToRecord', () => {
  it('converts entries to record, skipping empty keys', () => {
    const entries = [
      { key: 'provider', value: 'openai' },
      { key: '', value: 'ignored' },
      { key: 'model', value: 'gpt-4o' },
    ];
    expect(metadataEntriesToRecord(entries)).toEqual({
      provider: 'openai',
      model: 'gpt-4o',
    });
  });

  it('returns undefined for all-empty entries', () => {
    expect(metadataEntriesToRecord([{ key: '', value: '' }])).toBeUndefined();
    expect(metadataEntriesToRecord([])).toBeUndefined();
  });
});

describe('recordToMetadataEntries', () => {
  it('converts record to entries', () => {
    const result = recordToMetadataEntries({ provider: 'openai', model: 'gpt-4o' });
    expect(result).toEqual([
      { key: 'provider', value: 'openai' },
      { key: 'model', value: 'gpt-4o' },
    ]);
  });

  it('returns empty array for null/undefined', () => {
    expect(recordToMetadataEntries(null)).toEqual([]);
    expect(recordToMetadataEntries(undefined)).toEqual([]);
  });
});

describe('buildAutoMetadata', () => {
  it('builds entries from config params', () => {
    const result = buildAutoMetadata({
      providerName: 'openai',
      modelName: 'gpt-4o',
      temperature: 0.7,
      topP: 0.9,
    });
    expect(result).toEqual([
      { key: 'provider', value: 'openai' },
      { key: 'model', value: 'gpt-4o' },
      { key: 'temperature', value: '0.7' },
      { key: 'top_p', value: '0.9' },
    ]);
  });

  it('skips undefined params', () => {
    const result = buildAutoMetadata({ providerName: 'openai' });
    expect(result).toEqual([{ key: 'provider', value: 'openai' }]);
  });

  it('returns empty array for no params', () => {
    expect(buildAutoMetadata({})).toEqual([]);
  });
});

describe('buildRAGAutoMetadata', () => {
  it('builds entries from RAG config params', () => {
    const result = buildRAGAutoMetadata({
      backendType: 'http',
      endpointUrl: 'https://rag.example.com/query',
      embeddingModel: 'bge-large',
      generatorProviderId: 'openai',
    });
    expect(result).toEqual([
      { key: 'backend_type', value: 'http' },
      { key: 'endpoint_url', value: 'https://rag.example.com/query' },
      { key: 'embedding_model', value: 'bge-large' },
      { key: 'generator_provider', value: 'openai' },
    ]);
  });

  it('includes table_name for pgvector backend', () => {
    const result = buildRAGAutoMetadata({
      backendType: 'pgvector',
      tableName: 'embeddings',
    });
    expect(result).toEqual([
      { key: 'backend_type', value: 'pgvector' },
      { key: 'table_name', value: 'embeddings' },
    ]);
  });

  it('skips undefined params', () => {
    const result = buildRAGAutoMetadata({ backendType: 'http' });
    expect(result).toEqual([{ key: 'backend_type', value: 'http' }]);
  });

  it('returns empty array for no params', () => {
    expect(buildRAGAutoMetadata({})).toEqual([]);
  });
});

describe('buildArenaAutoMetadata', () => {
  it('builds entries from arena config', () => {
    const result = buildArenaAutoMetadata({
      contestantCount: 3,
      contestantModels: ['gpt-4o', 'claude-3.5-sonnet', 'gemini-pro'],
      temperature: 0.5,
      topP: 0.95,
    });
    expect(result).toEqual([
      { key: 'contestant_count', value: '3' },
      { key: 'contestant_models', value: 'gpt-4o, claude-3.5-sonnet, gemini-pro' },
      { key: 'temperature', value: '0.5' },
      { key: 'top_p', value: '0.95' },
    ]);
  });

  it('skips undefined params', () => {
    const result = buildArenaAutoMetadata({ contestantCount: 2 });
    expect(result).toEqual([{ key: 'contestant_count', value: '2' }]);
  });

  it('skips empty contestant models array', () => {
    const result = buildArenaAutoMetadata({ contestantModels: [] });
    expect(result).toEqual([]);
  });

  it('returns empty array for no params', () => {
    expect(buildArenaAutoMetadata({})).toEqual([]);
  });
});
