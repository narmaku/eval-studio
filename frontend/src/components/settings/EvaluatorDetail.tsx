import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { api } from '@/services/api';
import type { EvaluatorInfo } from '@/types';

interface ConfigFileEntry {
  filename: string;
  size: number;
  modified_at: string;
}

interface SchemaProperty {
  type?: string;
  description?: string;
  default?: unknown;
}

interface EvaluatorDetailProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  evaluator: EvaluatorInfo;
}

export function EvaluatorDetail({ open, onOpenChange, evaluator }: EvaluatorDetailProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent size="wide" className="overflow-y-auto">
        <EvaluatorDetailContent key={evaluator.id} evaluator={evaluator} />
      </SheetContent>
    </Sheet>
  );
}

function EvaluatorDetailContent({ evaluator }: { evaluator: EvaluatorInfo }) {
  const [configFiles, setConfigFiles] = useState<ConfigFileEntry[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState<{ filename: string; content: string } | null>(
    null,
  );
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchConfigFiles = useCallback(async () => {
    try {
      const files = await api.listEvaluatorConfigFiles(evaluator.id);
      setConfigFiles(files);
    } catch {
      // silently handle - empty state will be shown
    }
  }, [evaluator.id]);

  useEffect(() => {
    let cancelled = false;
    api.listEvaluatorConfigFiles(evaluator.id).then(
      (files) => {
        if (!cancelled) setConfigFiles(files);
      },
      () => {
        // silently handle
      },
    );
    return () => {
      cancelled = true;
    };
  }, [evaluator.id]);

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    try {
      await api.uploadEvaluatorConfigFile(evaluator.id, selectedFile);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await fetchConfigFiles();
    } catch {
      // handle error silently
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (filename: string) => {
    try {
      await api.deleteEvaluatorConfigFile(evaluator.id, filename);
      setConfirmDelete(null);
      await fetchConfigFiles();
    } catch {
      // handle error silently
    }
  };

  const handleView = async (filename: string) => {
    if (fileContent?.filename === filename) {
      setFileContent(null);
      return;
    }
    try {
      const content = await api.getEvaluatorConfigFile(evaluator.id, filename);
      setFileContent({ filename, content: String(content) });
    } catch {
      // handle error silently
    }
  };

  const schemaProperties = (evaluator.config_schema?.properties ?? {}) as Record<
    string,
    SchemaProperty
  >;
  const hasSchema = Object.keys(schemaProperties).length > 0;
  const hasDefaults = Object.keys(evaluator.defaults).length > 0;

  return (
    <>
      <SheetHeader>
        <SheetTitle className="text-lg">{evaluator.name}</SheetTitle>
        <SheetDescription>{evaluator.description}</SheetDescription>
      </SheetHeader>

      <div className="space-y-6 px-4 pb-4">
        {/* Info badges */}
        <div className="flex flex-wrap items-center gap-2">
          {evaluator.builtin && <Badge variant="outline">Built-in</Badge>}
          <StatusDot available={evaluator.available} />
          {evaluator.modes.map((mode) => (
            <Badge key={mode} variant="secondary" className="text-xs">
              {mode}
            </Badge>
          ))}
        </div>

        <Separator />

        {/* Default Configuration */}
        <section>
          <h4 className="mb-2 font-medium">Default Configuration</h4>
          {hasDefaults ? (
            <div className="rounded-md border">
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(evaluator.defaults).map(([key, value]) => (
                    <tr key={key} className="border-b last:border-0">
                      <td className="px-3 py-2 font-medium">{key}</td>
                      <td className="px-3 py-2 text-muted-foreground">{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No default configuration</p>
          )}
        </section>

        <Separator />

        {/* Configuration Schema */}
        <section>
          <h4 className="mb-1 font-medium">Available configuration options</h4>
          <p className="mb-3 text-xs text-muted-foreground">
            These options can be configured when creating an evaluation
          </p>
          {hasSchema ? (
            <div className="space-y-3">
              {Object.entries(schemaProperties).map(([name, prop]) => (
                <div key={name} className="rounded-md border p-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{name}</span>
                    {prop.type && (
                      <Badge variant="outline" className="text-xs">
                        {prop.type}
                      </Badge>
                    )}
                  </div>
                  {prop.description && (
                    <p className="mt-1 text-sm text-muted-foreground">{prop.description}</p>
                  )}
                  {prop.default !== undefined && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Default: {String(prop.default)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No configurable options</p>
          )}
        </section>

        <Separator />

        {/* Config Files */}
        <section>
          <h4 className="mb-3 font-medium">Configuration Files</h4>

          {/* Upload */}
          <div className="mb-4 flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              data-testid="config-file-input"
              className="flex-1 text-sm"
              onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            />
            <Button size="sm" onClick={handleUpload} disabled={!selectedFile || isUploading}>
              Upload
            </Button>
          </div>

          {/* File list */}
          {configFiles.length > 0 ? (
            <div className="space-y-2">
              {configFiles.map((f) => (
                <div key={f.filename}>
                  <div className="flex items-center justify-between rounded-md border p-2">
                    <div>
                      <span className="text-sm font-medium">{f.filename}</span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {formatSize(f.size)}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => handleView(f.filename)}>
                        {fileContent?.filename === f.filename ? 'Hide' : 'View'}
                      </Button>
                      {confirmDelete === f.filename ? (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(f.filename)}
                        >
                          Confirm
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setConfirmDelete(f.filename)}
                        >
                          Delete
                        </Button>
                      )}
                    </div>
                  </div>
                  {fileContent?.filename === f.filename && (
                    <pre className="mt-1 overflow-x-auto rounded-md bg-muted p-3 text-xs">
                      {fileContent.content}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No config files uploaded</p>
          )}
        </section>
      </div>
    </>
  );
}

function StatusDot({ available }: { available: boolean }) {
  return (
    <span className="flex items-center gap-1 text-xs">
      <span
        className={`inline-block h-2 w-2 rounded-full ${available ? 'bg-green-500' : 'bg-red-500'}`}
      />
      {available ? 'Available' : 'Unavailable'}
    </span>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
