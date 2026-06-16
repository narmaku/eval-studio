import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RAGEndpointConfig } from './RAGEndpointConfig';

describe('RAGEndpointConfig', () => {
  describe('default / HTTP backend', () => {
    it('renders backend type selector and HTTP fields by default', () => {
      const onChange = vi.fn();
      render(<RAGEndpointConfig value={undefined} onChange={onChange} />);

      expect(screen.getByText('RAG Backend Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText('Endpoint URL')).toBeInTheDocument();
      expect(screen.getByLabelText('Auth Token Env Var (optional)')).toBeInTheDocument();
      expect(screen.getByLabelText('Query Field Name')).toBeInTheDocument();
      expect(screen.getByLabelText('Answer Field Name')).toBeInTheDocument();
      expect(screen.getByLabelText('Chunks Field Name')).toBeInTheDocument();
    });

    it('does not render pgvector fields when HTTP is selected', () => {
      const onChange = vi.fn();
      render(<RAGEndpointConfig value={undefined} onChange={onChange} />);

      expect(screen.queryByLabelText('Connection String')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Table Name')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Embedding Column')).not.toBeInTheDocument();
    });

    it('renders with provided HTTP values', () => {
      const onChange = vi.fn();
      render(
        <RAGEndpointConfig
          value={{
            backend_type: 'http',
            endpoint_url: 'https://rag.example.com/query',
            auth_token_env: 'RAG_AUTH_TOKEN',
            query_field: 'q',
            answer_field: 'a',
            chunks_field: 'docs',
          }}
          onChange={onChange}
        />,
      );

      expect(screen.getByLabelText('Endpoint URL')).toHaveValue('https://rag.example.com/query');
      expect(screen.getByLabelText('Auth Token Env Var (optional)')).toHaveValue('RAG_AUTH_TOKEN');
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
          backend_type: 'http',
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
            backend_type: 'http',
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
          backend_type: 'http',
          endpoint_url: 'https://example.com',
          query_field: 'question',
        }),
      );
    });

    it('disables all inputs when disabled prop is true', () => {
      const onChange = vi.fn();
      render(<RAGEndpointConfig value={undefined} onChange={onChange} disabled />);

      expect(screen.getByLabelText('Endpoint URL')).toBeDisabled();
      expect(screen.getByLabelText('Auth Token Env Var (optional)')).toBeDisabled();
      expect(screen.getByLabelText('Query Field Name')).toBeDisabled();
      expect(screen.getByLabelText('Answer Field Name')).toBeDisabled();
      expect(screen.getByLabelText('Chunks Field Name')).toBeDisabled();
    });
  });

  describe('pgvector backend', () => {
    it('renders pgvector fields when pgvector is selected', () => {
      const onChange = vi.fn();
      render(
        <RAGEndpointConfig
          value={{
            backend_type: 'pgvector',
            connection_string: '',
            table_name: '',
            content_column: 'content',
            embedding_column: 'embedding',
            top_k: 5,
            generator_provider_id: '',
            embedding_model: 'text-embedding-3-small',
          }}
          onChange={onChange}
        />,
      );

      expect(screen.getByLabelText('Connection String')).toBeInTheDocument();
      expect(screen.getByLabelText('Table Name')).toBeInTheDocument();
      expect(screen.getByLabelText('Content Column')).toBeInTheDocument();
      expect(screen.getByLabelText('Embedding Column')).toBeInTheDocument();
      expect(screen.getByLabelText('Top K Results')).toBeInTheDocument();
      expect(screen.getByLabelText('Generator Provider ID')).toBeInTheDocument();
      expect(screen.getByLabelText('Generator API Key Env Var (optional)')).toBeInTheDocument();
      expect(screen.getByLabelText('Embedding Model')).toBeInTheDocument();
    });

    it('does not render HTTP fields when pgvector is selected', () => {
      const onChange = vi.fn();
      render(
        <RAGEndpointConfig
          value={{
            backend_type: 'pgvector',
            connection_string: '',
            table_name: '',
          }}
          onChange={onChange}
        />,
      );

      expect(screen.queryByLabelText('Endpoint URL')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Auth Token Env Var (optional)')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Query Field Name')).not.toBeInTheDocument();
    });

    it('renders with provided pgvector values', () => {
      const onChange = vi.fn();
      render(
        <RAGEndpointConfig
          value={{
            backend_type: 'pgvector',
            connection_string: 'postgresql://user:pass@localhost:5432/mydb',
            table_name: 'documents',
            content_column: 'text',
            embedding_column: 'vec',
            top_k: 10,
            generator_provider_id: 'openai-1',
            embedding_model: 'text-embedding-ada-002',
          }}
          onChange={onChange}
        />,
      );

      expect(screen.getByLabelText('Connection String')).toHaveValue(
        'postgresql://user:pass@localhost:5432/mydb',
      );
      expect(screen.getByLabelText('Table Name')).toHaveValue('documents');
      expect(screen.getByLabelText('Content Column')).toHaveValue('text');
      expect(screen.getByLabelText('Embedding Column')).toHaveValue('vec');
      expect(screen.getByLabelText('Top K Results')).toHaveValue(10);
      expect(screen.getByLabelText('Generator Provider ID')).toHaveValue('openai-1');
      expect(screen.getByLabelText('Embedding Model')).toHaveValue('text-embedding-ada-002');
    });

    it('emits config on connection string change', () => {
      const onChange = vi.fn();
      render(
        <RAGEndpointConfig
          value={{
            backend_type: 'pgvector',
            connection_string: '',
            table_name: 'docs',
          }}
          onChange={onChange}
        />,
      );

      const connInput = screen.getByLabelText('Connection String');
      fireEvent.change(connInput, {
        target: { value: 'postgresql://u:p@host:5432/db' },
      });

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          backend_type: 'pgvector',
          connection_string: 'postgresql://u:p@host:5432/db',
          table_name: 'docs',
        }),
      );
    });

    it('emits config on top_k change with parsed number', () => {
      const onChange = vi.fn();
      render(
        <RAGEndpointConfig
          value={{
            backend_type: 'pgvector',
            connection_string: 'postgresql://localhost/db',
            table_name: 'docs',
            top_k: 5,
          }}
          onChange={onChange}
        />,
      );

      const topKInput = screen.getByLabelText('Top K Results');
      fireEvent.change(topKInput, { target: { value: '10' } });

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          backend_type: 'pgvector',
          top_k: 10,
        }),
      );
    });

    it('disables all pgvector inputs when disabled prop is true', () => {
      const onChange = vi.fn();
      render(
        <RAGEndpointConfig
          value={{
            backend_type: 'pgvector',
            connection_string: '',
            table_name: '',
          }}
          onChange={onChange}
          disabled
        />,
      );

      expect(screen.getByLabelText('Connection String')).toBeDisabled();
      expect(screen.getByLabelText('Table Name')).toBeDisabled();
      expect(screen.getByLabelText('Content Column')).toBeDisabled();
      expect(screen.getByLabelText('Embedding Column')).toBeDisabled();
      expect(screen.getByLabelText('Top K Results')).toBeDisabled();
      expect(screen.getByLabelText('Generator Provider ID')).toBeDisabled();
      expect(screen.getByLabelText('Embedding Model')).toBeDisabled();
    });
  });

  it('displays card title', () => {
    const onChange = vi.fn();
    render(<RAGEndpointConfig value={undefined} onChange={onChange} />);

    expect(screen.getByText('RAG Backend Configuration')).toBeInTheDocument();
  });
});
