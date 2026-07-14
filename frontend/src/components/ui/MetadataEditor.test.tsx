import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MetadataEditor } from './MetadataEditor';

describe('MetadataEditor', () => {
  it('renders empty state text when no entries', () => {
    render(<MetadataEditor entries={[]} onChange={vi.fn()} />);
    expect(
      screen.getByText('No metadata entries. Click Add to include key-value pairs.'),
    ).toBeInTheDocument();
  });

  it('renders custom empty text', () => {
    render(<MetadataEditor entries={[]} onChange={vi.fn()} emptyText="Nothing here." />);
    expect(screen.getByText('Nothing here.')).toBeInTheDocument();
  });

  it('renders custom label', () => {
    render(<MetadataEditor entries={[]} onChange={vi.fn()} label="Tags" />);
    expect(screen.getByText('Tags')).toBeInTheDocument();
  });

  it('calls onChange with new entry when Add is clicked', () => {
    const onChange = vi.fn();
    render(<MetadataEditor entries={[]} onChange={onChange} />);
    fireEvent.click(screen.getByText('Add'));
    expect(onChange).toHaveBeenCalledWith([{ key: '', value: '' }]);
  });

  it('renders existing entries with key and value inputs', () => {
    const entries = [
      { key: 'provider', value: 'openai' },
      { key: 'model', value: 'gpt-4o' },
    ];
    render(<MetadataEditor entries={entries} onChange={vi.fn()} />);
    expect(screen.getByDisplayValue('provider')).toBeInTheDocument();
    expect(screen.getByDisplayValue('openai')).toBeInTheDocument();
    expect(screen.getByDisplayValue('model')).toBeInTheDocument();
    expect(screen.getByDisplayValue('gpt-4o')).toBeInTheDocument();
  });

  it('removes entry when remove button is clicked', () => {
    const onChange = vi.fn();
    const entries = [
      { key: 'provider', value: 'openai' },
      { key: 'model', value: 'gpt-4o' },
    ];
    render(<MetadataEditor entries={entries} onChange={onChange} />);
    const removeButtons = screen.getAllByLabelText(/Remove metadata entry/);
    fireEvent.click(removeButtons[0]!);
    expect(onChange).toHaveBeenCalledWith([{ key: 'model', value: 'gpt-4o' }]);
  });

  it('updates entry key when input changes', () => {
    const onChange = vi.fn();
    const entries = [{ key: 'old', value: 'val' }];
    render(<MetadataEditor entries={entries} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('Metadata key 1'), {
      target: { value: 'new' },
    });
    expect(onChange).toHaveBeenCalledWith([{ key: 'new', value: 'val' }]);
  });

  it('updates entry value when input changes', () => {
    const onChange = vi.fn();
    const entries = [{ key: 'k', value: 'old' }];
    render(<MetadataEditor entries={entries} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('Metadata value 1'), {
      target: { value: 'new' },
    });
    expect(onChange).toHaveBeenCalledWith([{ key: 'k', value: 'new' }]);
  });

  it('disables Add button when max entries reached', () => {
    const entries = Array.from({ length: 20 }, (_, i) => ({
      key: `key${i}`,
      value: `val${i}`,
    }));
    render(<MetadataEditor entries={entries} onChange={vi.fn()} />);
    expect(screen.getByText('Add').closest('button')).toBeDisabled();
  });

  it('truncates key to max 50 characters', () => {
    const onChange = vi.fn();
    const entries = [{ key: '', value: '' }];
    render(<MetadataEditor entries={entries} onChange={onChange} />);
    const longKey = 'a'.repeat(60);
    fireEvent.change(screen.getByLabelText('Metadata key 1'), {
      target: { value: longKey },
    });
    expect(onChange).toHaveBeenCalledWith([{ key: 'a'.repeat(50), value: '' }]);
  });

  it('truncates value to max 200 characters', () => {
    const onChange = vi.fn();
    const entries = [{ key: 'k', value: '' }];
    render(<MetadataEditor entries={entries} onChange={onChange} />);
    const longVal = 'b'.repeat(210);
    fireEvent.change(screen.getByLabelText('Metadata value 1'), {
      target: { value: longVal },
    });
    expect(onChange).toHaveBeenCalledWith([{ key: 'k', value: 'b'.repeat(200) }]);
  });
});
