import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Copy, Check, Download, Eye, Loader2, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { api } from '@/services/api';
import type { Artifact } from '@/types';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

// Allowlist of content types safe for inline preview.
// text/html and text/xml are excluded to prevent stored XSS.
const PREVIEWABLE_TYPES = new Set(['text/plain', 'text/csv', 'text/markdown', 'application/json']);

function isPreviewable(contentType: string): boolean {
  return PREVIEWABLE_TYPES.has(contentType);
}

/* ---------- JSON helpers ---------- */

function tryParseJson(text: string): unknown | undefined {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

/* ---------- CSV helper ---------- */

function parseCsv(text: string): string[][] {
  return text
    .trim()
    .split('\n')
    .map((line) => line.split(',').map((cell) => cell.trim()));
}

/* ---------- Renderer: JSON ---------- */

function JsonValue({ value, indent = 0 }: { value: unknown; indent?: number }): React.JSX.Element {
  const pad = '  '.repeat(indent);
  const padInner = '  '.repeat(indent + 1);

  if (value === null) {
    return <span className="text-[var(--warn)]">null</span>;
  }

  if (typeof value === 'boolean') {
    return <span className="text-[var(--warn)]">{String(value)}</span>;
  }

  if (typeof value === 'number') {
    return <span className="text-[var(--accent-2)]">{String(value)}</span>;
  }

  if (typeof value === 'string') {
    return <span className="text-[var(--pass)]">&quot;{value}&quot;</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span>{'[]'}</span>;
    return (
      <span>
        {'[\n'}
        {value.map((item, i) => (
          <span key={i}>
            {padInner}
            <JsonValue value={item} indent={indent + 1} />
            {i < value.length - 1 ? ',' : ''}
            {'\n'}
          </span>
        ))}
        {pad}
        {']'}
      </span>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return <span>{'{}'}</span>;
    return (
      <span>
        {'{\n'}
        {entries.map(([key, val], i) => (
          <span key={key}>
            {padInner}
            <span className="text-[var(--accent)]">&quot;{key}&quot;</span>
            {': '}
            <JsonValue value={val} indent={indent + 1} />
            {i < entries.length - 1 ? ',' : ''}
            {'\n'}
          </span>
        ))}
        {pad}
        {'}'}
      </span>
    );
  }

  return <span>{String(value)}</span>;
}

function JsonPreview({ content }: { content: string }): React.JSX.Element {
  const parsed = useMemo(() => tryParseJson(content), [content]);

  if (parsed === undefined) {
    return <PlainTextPreview content={content} />;
  }

  return (
    <pre className="text-xs bg-muted/50 p-4 rounded-md overflow-x-auto whitespace-pre-wrap break-words">
      <JsonValue value={parsed} />
    </pre>
  );
}

/* ---------- Renderer: CSV ---------- */

function CsvPreview({ content }: { content: string }): React.JSX.Element {
  const rows = useMemo(() => parseCsv(content), [content]);
  const [header, ...body] = rows;

  if (!header || header.length === 0) {
    return <PlainTextPreview content={content} />;
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            {header.map((cell, i) => (
              <TableHead key={i}>{cell}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {body.map((row, ri) => (
            <TableRow key={ri}>
              {row.map((cell, ci) => (
                <TableCell key={ci}>{cell}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/* ---------- Renderer: Markdown ---------- */

function MarkdownPreview({ content }: { content: string }): React.JSX.Element {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}

/* ---------- Renderer: Plain text ---------- */

function PlainTextPreview({ content }: { content: string }): React.JSX.Element {
  return (
    <pre className="text-xs bg-muted/50 p-4 rounded-md overflow-x-auto whitespace-pre-wrap break-words">
      {content}
    </pre>
  );
}

/* ---------- Content switcher ---------- */

function PreviewContent({
  content,
  contentType,
}: {
  content: string;
  contentType: string;
}): React.JSX.Element {
  switch (contentType) {
    case 'application/json':
      return <JsonPreview content={content} />;
    case 'text/csv':
      return <CsvPreview content={content} />;
    case 'text/markdown':
      return <MarkdownPreview content={content} />;
    default:
      return <PlainTextPreview content={content} />;
  }
}

/* ---------- Content type label ---------- */

function contentTypeLabel(contentType: string): string {
  switch (contentType) {
    case 'application/json':
      return 'JSON';
    case 'text/csv':
      return 'CSV';
    case 'text/markdown':
      return 'Markdown';
    case 'text/plain':
      return 'Text';
    default:
      return contentType;
  }
}

/* ---------- Main component ---------- */

interface ArtifactsListProps {
  evaluationId: string;
}

export function ArtifactsList({ evaluationId }: ArtifactsListProps): React.JSX.Element | null {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewArtifact, setPreviewArtifact] = useState<Artifact | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      try {
        const data = await api.listArtifacts(evaluationId);
        if (!cancelled) {
          setArtifacts(data.items);
          setError(null);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load artifacts';
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [evaluationId]);

  const handlePreview = async (artifact: Artifact) => {
    setIsPreviewLoading(true);
    setPreviewArtifact(artifact);
    setCopied(false);
    try {
      const content = await api.previewArtifact(artifact.id);
      setPreviewContent(content);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load preview';
      setPreviewContent(`Error loading preview: ${message}`);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleDownload = (artifact: Artifact) => {
    const url = api.getArtifactDownloadUrl(artifact.id);
    window.open(url, '_blank');
  };

  const handleCopy = useCallback(async () => {
    if (!previewContent) return;
    try {
      await navigator.clipboard.writeText(previewContent);
      setCopied(true);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch (err: unknown) {
      console.warn('Clipboard write failed:', err instanceof Error ? err.message : err);
    }
  }, [previewContent]);

  const closePreview = useCallback(() => {
    if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
    setPreviewArtifact(null);
    setPreviewContent(null);
    setCopied(false);
  }, []);

  // Don't render anything if loading, no artifacts, or error
  if (isLoading) {
    return null;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-4">
          <p className="text-destructive text-sm text-center">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (artifacts.length === 0) {
    return null;
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Artifacts
            <Badge variant="outline" className="text-xs">
              {artifacts.length}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {artifacts.map((artifact) => (
                  <TableRow key={artifact.id}>
                    <TableCell className="font-mono text-sm">{artifact.filename}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {artifact.content_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {formatFileSize(artifact.size_bytes)}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-muted-foreground text-sm">
                      {artifact.description ?? '--'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {isPreviewable(artifact.content_type) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => void handlePreview(artifact)}
                            title="Preview"
                          >
                            <Eye className="h-4 w-4" />
                            <span className="sr-only">Preview {artifact.filename}</span>
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownload(artifact)}
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                          <span className="sr-only">Download {artifact.filename}</span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={previewArtifact !== null} onOpenChange={(open) => !open && closePreview()}>
        <DialogContent className="max-w-5xl sm:max-w-5xl max-h-[85vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-mono text-sm">
              {previewArtifact?.filename}
              {previewArtifact && (
                <Badge variant="secondary" className="text-xs font-sans">
                  {contentTypeLabel(previewArtifact.content_type)}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>
          <div className="overflow-auto max-h-[60vh]">
            {isPreviewLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : previewContent !== null && previewArtifact ? (
              <PreviewContent content={previewContent} contentType={previewArtifact.content_type} />
            ) : null}
          </div>
          <DialogFooter showCloseButton>
            {previewContent !== null && (
              <Button
                variant="outline"
                size="sm"
                className="mr-auto"
                onClick={() => void handleCopy()}
              >
                {copied ? <Check className="h-4 w-4 mr-1" /> : <Copy className="h-4 w-4 mr-1" />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
            )}
            {previewArtifact && (
              <Button variant="outline" size="sm" onClick={() => handleDownload(previewArtifact)}>
                <Download className="h-4 w-4 mr-1" />
                Download
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
