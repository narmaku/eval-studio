import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { RAGEndpointSettings } from '@/types';

export type { RAGEndpointSettings } from '@/types';

interface RAGEndpointConfigProps {
  value: RAGEndpointSettings | undefined;
  onChange: (config: RAGEndpointSettings) => void;
  disabled?: boolean;
}

const DEFAULT_SETTINGS: RAGEndpointSettings = {
  endpoint_url: '',
  auth_header: '',
  query_field: 'query',
  answer_field: 'answer',
  chunks_field: 'source_documents',
};

export function RAGEndpointConfig({ value, onChange, disabled }: RAGEndpointConfigProps) {
  const settings = value ?? DEFAULT_SETTINGS;

  const handleChange = (field: keyof RAGEndpointSettings, fieldValue: string) => {
    onChange({
      ...settings,
      [field]: fieldValue,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">RAG Endpoint</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="rag-endpoint-url">Endpoint URL</Label>
          <Input
            id="rag-endpoint-url"
            placeholder="https://your-rag-api.example.com/query"
            value={settings.endpoint_url}
            onChange={(e) => handleChange('endpoint_url', e.target.value)}
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
            onChange={(e) => handleChange('auth_header', e.target.value)}
            disabled={disabled}
          />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="rag-query-field">Query Field Name</Label>
            <Input
              id="rag-query-field"
              placeholder="query"
              value={settings.query_field}
              onChange={(e) => handleChange('query_field', e.target.value)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="rag-answer-field">Answer Field Name</Label>
            <Input
              id="rag-answer-field"
              placeholder="answer"
              value={settings.answer_field}
              onChange={(e) => handleChange('answer_field', e.target.value)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="rag-chunks-field">Chunks Field Name</Label>
            <Input
              id="rag-chunks-field"
              placeholder="source_documents"
              value={settings.chunks_field}
              onChange={(e) => handleChange('chunks_field', e.target.value)}
              disabled={disabled}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
