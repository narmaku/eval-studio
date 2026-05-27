import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RAGEndpointConfig } from './RAGEndpointConfig';

describe('RAGEndpointConfig', () => {
  it('renders all form fields', () => {
    const onChange = vi.fn();
    render(<RAGEndpointConfig value={undefined} onChange={onChange} />);

    expect(screen.getByLabelText('Endpoint URL')).toBeInTheDocument();
    expect(screen.getByLabelText('Auth Header Value (optional)')).toBeInTheDocument();
    expect(screen.getByLabelText('Query Field Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Answer Field Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Chunks Field Name')).toBeInTheDocument();
  });

  it('renders with provided values', () => {
    const onChange = vi.fn();
    render(
      <RAGEndpointConfig
        value={{
          endpoint_url: 'https://rag.example.com/query',
          auth_header: 'Bearer abc123',
          query_field: 'q',
          answer_field: 'a',
          chunks_field: 'docs',
        }}
        onChange={onChange}
      />,
    );

    expect(screen.getByLabelText('Endpoint URL')).toHaveValue('https://rag.example.com/query');
    expect(screen.getByLabelText('Auth Header Value (optional)')).toHaveValue('Bearer abc123');
    expect(screen.getByLabelText('Query Field Name')).toHaveValue('q');
    expect(screen.getByLabelText('Answer Field Name')).toHaveValue('a');
    expect(screen.getByLabelText('Chunks Field Name')).toHaveValue('docs');
  });

  it('emits config on endpoint URL change', () => {
    const onChange = vi.fn();
    render(<RAGEndpointConfig value={undefined} onChange={onChange} />);

    const urlInput = screen.getByLabelText('Endpoint URL');
    fireEvent.change(urlInput, { target: { value: 'https://api.test.com' } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        endpoint_url: 'https://api.test.com',
        query_field: 'query',
        answer_field: 'answer',
        chunks_field: 'source_documents',
      }),
    );
  });

  it('emits config on query field name change', () => {
    const onChange = vi.fn();
    render(
      <RAGEndpointConfig
        value={{
          endpoint_url: 'https://example.com',
          query_field: 'query',
          answer_field: 'answer',
          chunks_field: 'source_documents',
        }}
        onChange={onChange}
      />,
    );

    const queryInput = screen.getByLabelText('Query Field Name');
    fireEvent.change(queryInput, { target: { value: 'question' } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        endpoint_url: 'https://example.com',
        query_field: 'question',
      }),
    );
  });

  it('disables all inputs when disabled prop is true', () => {
    const onChange = vi.fn();
    render(<RAGEndpointConfig value={undefined} onChange={onChange} disabled />);

    expect(screen.getByLabelText('Endpoint URL')).toBeDisabled();
    expect(screen.getByLabelText('Auth Header Value (optional)')).toBeDisabled();
    expect(screen.getByLabelText('Query Field Name')).toBeDisabled();
    expect(screen.getByLabelText('Answer Field Name')).toBeDisabled();
    expect(screen.getByLabelText('Chunks Field Name')).toBeDisabled();
  });

  it('displays card title', () => {
    const onChange = vi.fn();
    render(<RAGEndpointConfig value={undefined} onChange={onChange} />);

    expect(screen.getByText('RAG Endpoint')).toBeInTheDocument();
  });
});
