import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { RAGEndpointSettings } from '@/types';

export type { RAGEndpointSettings } from '@/types';

interface RAGEndpointConfigProps {
  value: RAGEndpointSettings | undefined;
  onChange: (config: RAGEndpointSettings) => void;
  disabled?: boolean;
}

const DEFAULT_HTTP_SETTINGS: RAGEndpointSettings = {
  backend_type: 'http',
  endpoint_url: '',
  auth_header: '',
  query_field: 'query',
  answer_field: 'answer',
  chunks_field: 'source_documents',
};

const DEFAULT_PGVECTOR_SETTINGS: RAGEndpointSettings = {
  backend_type: 'pgvector',
  connection_string: '',
  table_name: '',
  content_column: 'content',
  embedding_column: 'embedding',
  top_k: 5,
  generator_provider_id: '',
  embedding_model: 'text-embedding-3-small',
};

function getDefaults(backendType: 'http' | 'pgvector'): RAGEndpointSettings {
  return backendType === 'pgvector'
    ? { ...DEFAULT_PGVECTOR_SETTINGS }
    : { ...DEFAULT_HTTP_SETTINGS };
}

export function RAGEndpointConfig({ value, onChange, disabled }: RAGEndpointConfigProps) {
  const settings = value ?? DEFAULT_HTTP_SETTINGS;

  const handleBackendTypeChange = (newType: 'http' | 'pgvector') => {
    onChange(getDefaults(newType));
  };

  const handleStringChange = (field: keyof RAGEndpointSettings, fieldValue: string) => {
    onChange({
      ...settings,
      [field]: fieldValue,
    });
  };

  const handleNumberChange = (field: keyof RAGEndpointSettings, fieldValue: string) => {
    const parsed = parseInt(fieldValue, 10);
    onChange({
      ...settings,
      [field]: isNaN(parsed) ? undefined : parsed,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">RAG Backend Configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="rag-backend-type">Backend Type</Label>
          <Select
            value={settings.backend_type}
            onValueChange={(val) => handleBackendTypeChange(val as 'http' | 'pgvector')}
            disabled={disabled}
          >
            <SelectTrigger id="rag-backend-type" className="w-full">
              <SelectValue placeholder="Select backend type..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="http">HTTP Endpoint</SelectItem>
              <SelectItem value="pgvector">PostgreSQL + pgvector</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {settings.backend_type === 'http' && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="rag-endpoint-url">Endpoint URL</Label>
              <Input
                id="rag-endpoint-url"
                placeholder="https://your-rag-api.example.com/query"
                value={settings.endpoint_url ?? ''}
                onChange={(e) => handleStringChange('endpoint_url', e.target.value)}
                disabled={disabled}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rag-auth-header">Auth Header Value (optional)</Label>
              <Input
                id="rag-auth-header"
                placeholder="Bearer token..."
                value={settings.auth_header ?? ''}
                onChange={(e) => handleStringChange('auth_header', e.target.value)}
                disabled={disabled}
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="rag-query-field">Query Field Name</Label>
                <Input
                  id="rag-query-field"
                  placeholder="query"
                  value={settings.query_field ?? 'query'}
                  onChange={(e) => handleStringChange('query_field', e.target.value)}
                  disabled={disabled}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="rag-answer-field">Answer Field Name</Label>
                <Input
                  id="rag-answer-field"
                  placeholder="answer"
                  value={settings.answer_field ?? 'answer'}
                  onChange={(e) => handleStringChange('answer_field', e.target.value)}
                  disabled={disabled}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="rag-chunks-field">Chunks Field Name</Label>
                <Input
                  id="rag-chunks-field"
                  placeholder="source_documents"
                  value={settings.chunks_field ?? 'source_documents'}
                  onChange={(e) => handleStringChange('chunks_field', e.target.value)}
                  disabled={disabled}
                />
              </div>
            </div>
          </>
        )}

        {settings.backend_type === 'pgvector' && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="rag-connection-string">Connection String</Label>
              <Input
                id="rag-connection-string"
                placeholder="postgresql://user:pass@host:5432/dbname"
                value={settings.connection_string ?? ''}
                onChange={(e) => handleStringChange('connection_string', e.target.value)}
                disabled={disabled}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rag-table-name">Table Name</Label>
              <Input
                id="rag-table-name"
                placeholder="documents"
                value={settings.table_name ?? ''}
                onChange={(e) => handleStringChange('table_name', e.target.value)}
                disabled={disabled}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="rag-content-column">Content Column</Label>
                <Input
                  id="rag-content-column"
                  placeholder="content"
                  value={settings.content_column ?? 'content'}
                  onChange={(e) => handleStringChange('content_column', e.target.value)}
                  disabled={disabled}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="rag-embedding-column">Embedding Column</Label>
                <Input
                  id="rag-embedding-column"
                  placeholder="embedding"
                  value={settings.embedding_column ?? 'embedding'}
                  onChange={(e) => handleStringChange('embedding_column', e.target.value)}
                  disabled={disabled}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rag-top-k">Top K Results</Label>
              <Input
                id="rag-top-k"
                type="number"
                min={1}
                placeholder="5"
                value={settings.top_k ?? 5}
                onChange={(e) => handleNumberChange('top_k', e.target.value)}
                disabled={disabled}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rag-generator-provider">Generator Provider ID</Label>
              <Input
                id="rag-generator-provider"
                placeholder="provider-id"
                value={settings.generator_provider_id ?? ''}
                onChange={(e) => handleStringChange('generator_provider_id', e.target.value)}
                disabled={disabled}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rag-embedding-model">Embedding Model</Label>
              <Input
                id="rag-embedding-model"
                placeholder="text-embedding-3-small"
                value={settings.embedding_model ?? 'text-embedding-3-small'}
                onChange={(e) => handleStringChange('embedding_model', e.target.value)}
                disabled={disabled}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
