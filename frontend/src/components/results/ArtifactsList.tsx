import { useEffect, useState, useRef } from 'react';
import { Download, Eye, Loader2, FileText } from 'lucide-react';
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

function isPreviewable(contentType: string): boolean {
  return contentType.startsWith('text/') || contentType === 'application/json';
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
  const prevEvaluationId = useRef<string | null>(null);

  useEffect(() => {
    // Only fetch if evaluationId actually changed
    if (prevEvaluationId.current === evaluationId) return;
    prevEvaluationId.current = evaluationId;

    let cancelled = false;

    async function load() {
      try {
        const data = await api.listArtifacts(evaluationId);
        if (!cancelled) {
          setArtifacts(data);
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

  const closePreview = () => {
    setPreviewArtifact(null);
    setPreviewContent(null);
  };

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
        <DialogContent className="max-w-2xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="font-mono text-sm">{previewArtifact?.filename}</DialogTitle>
          </DialogHeader>
          <div className="overflow-auto max-h-[60vh]">
            {isPreviewLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <pre className="text-xs bg-muted/50 p-4 rounded-md overflow-x-auto whitespace-pre-wrap break-words">
                {previewContent}
              </pre>
            )}
          </div>
          <DialogFooter showCloseButton>
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
