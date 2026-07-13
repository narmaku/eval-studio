import { useEffect, useState, useMemo } from 'react';
import { Download, Eye, Loader2, FileText, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
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

const PREVIEWABLE_TYPES = new Set(['text/plain', 'text/csv', 'text/markdown', 'application/json']);

function isPreviewable(contentType: string): boolean {
  return PREVIEWABLE_TYPES.has(contentType);
}

function tryParseJson(content: string): unknown | null {
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

function parseCsv(content: string): string[][] {
  return content
    .trim()
    .split('\n')
    .map((row) => row.split(',').map((cell) => cell.trim()));
}

function JsonValue({ value, indent = 0 }: { value: unknown; indent?: number }) {
  if (value === null) {
    return <span className="text-orange-500 dark:text-orange-400">null</span>;
  }

  if (typeof value === 'boolean') {
    return <span className="text-orange-500 dark:text-orange-400">{String(value)}</span>;
  }

  if (typeof value === 'number') {
    return <span className="text-blue-600 dark:text-blue-400">{String(value)}</span>;
  }

  if (typeof value === 'string') {
    return <span className="text-green-600 dark:text-green-400">&quot;{value}&quot;</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span>{'[]'}</span>;
    }
    const nextIndent = indent + 1;
    const padding = '  '.repeat(nextIndent);
    const closePadding = '  '.repeat(indent);
    return (
      <span>
        {'[\n'}
        {value.map((item, i) => (
          <span key={i}>
            {padding}
            <JsonValue value={item} indent={nextIndent} />
            {i < value.length - 1 ? ',' : ''}
            {'\n'}
          </span>
        ))}
        {closePadding}
        {']'}
      </span>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) {
      return <span>{'{}'}</span>;
    }
    const nextIndent = indent + 1;
    const padding = '  '.repeat(nextIndent);
    const closePadding = '  '.repeat(indent);
    return (
      <span>
        {'{\n'}
        {entries.map(([key, val], i) => (
          <span key={key}>
            {padding}
            <span className="text-violet-600 dark:text-violet-400">&quot;{key}&quot;</span>
            {': '}
            <JsonValue value={val} indent={nextIndent} />
            {i < entries.length - 1 ? ',' : ''}
            {'\n'}
          </span>
        ))}
        {closePadding}
        {'}'}
      </span>
    );
  }

  return <span>{String(value)}</span>;
}

function JsonPreview({ content }: { content: string }) {
  const parsed = useMemo(() => tryParseJson(content), [content]);

  if (parsed === null) {
    return (
      <pre className="text-xs font-mono bg-muted/50 p-4 rounded-md overflow-x-auto whitespace-pre-wrap break-words">
        {content}
      </pre>
    );
  }

  return (
    <pre className="text-xs font-mono bg-zinc-950 dark:bg-zinc-950 text-zinc-200 p-4 rounded-md overflow-x-auto whitespace-pre">
      <JsonValue value={parsed} />
    </pre>
  );
}

function CsvPreview({ content }: { content: string }) {
  const rows = useMemo(() => parseCsv(content), [content]);

  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Empty CSV</p>;
  }

  const [header, ...body] = rows;

  return (
    <div className="rounded-md border overflow-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {header!.map((cell, i) => (
              <TableHead key={i} className="text-xs font-medium whitespace-nowrap">
                {cell}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {body.map((row, ri) => (
            <TableRow key={ri}>
              {row.map((cell, ci) => (
                <TableCell key={ci} className="text-xs whitespace-nowrap">
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function MarkdownPreview({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

function PlainTextPreview({ content }: { content: string }) {
  return (
    <pre className="text-xs font-mono bg-muted/50 p-4 rounded-md overflow-x-auto whitespace-pre-wrap break-words">
      {content}
    </pre>
  );
}

function PreviewContent({ content, contentType }: { content: string; contentType: string }) {
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

interface ArtifactsListProps {
  evaluationId: string;
}

export function ArtifactsList({ evaluationId }: ArtifactsListProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewArtifact, setPreviewArtifact] = useState<Artifact | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [copied, setCopied] = useState(false);

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

  const handleCopy = async () => {
    if (!previewContent) return;
    await navigator.clipboard.writeText(previewContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const closePreview = () => {
    setPreviewArtifact(null);
    setPreviewContent(null);
    setCopied(false);
  };

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
        <DialogContent className="max-w-5xl max-h-[85vh]">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <DialogTitle className="font-mono text-sm">{previewArtifact?.filename}</DialogTitle>
              {previewArtifact && (
                <Badge variant="outline" className="text-xs">
                  {previewArtifact.content_type}
                </Badge>
              )}
            </div>
          </DialogHeader>
          <div className="overflow-auto max-h-[65vh]">
            {isPreviewLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : previewContent !== null ? (
              <PreviewContent
                content={previewContent}
                contentType={previewArtifact?.content_type ?? 'text/plain'}
              />
            ) : null}
          </div>
          <DialogFooter showCloseButton>
            {previewContent && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void handleCopy()}
                className="mr-auto"
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
