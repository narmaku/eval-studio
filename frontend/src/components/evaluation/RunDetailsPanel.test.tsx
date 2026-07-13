import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RunDetailsPanel } from './RunDetailsPanel';
import {
  metadataEntriesToRecord,
  recordToMetadataEntries,
  buildAutoMetadata,
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
