import { useState, useCallback, useRef, useMemo } from 'react';
import { Upload, X, FolderOpen, Loader2, ChevronLeft, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { useDatasetStore } from '@/stores/datasetStore';
import type { FieldMapping, MergeMode, AnalyzeResponse } from '@/types';

const ACCEPTED_EXTENSIONS = '.yaml,.yml,.jsonl,.ndjson,.json,.csv,.tsv';
const SKIP_VALUE = '__skip__';

interface SmartImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-green-100 text-green-800';
  if (confidence >= 0.5) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return 'High';
  if (confidence >= 0.5) return 'Medium';
  return 'Low';
}

function deriveMappingFromAnalysis(result: AnalyzeResponse | null): FieldMapping {
  if (result?.suggested_mapping) {
    return {
      question_field: result.suggested_mapping.question_field ?? '',
      answer_field: result.suggested_mapping.answer_field ?? '',
    };
  }
  return { question_field: '', answer_field: '' };
}

export function SmartImportDialog({ open, onOpenChange }: SmartImportDialogProps) {
  const {
    analysisResult,
    isAnalyzing,
    isImporting,
    analyzeFiles,
    smartImport,
    clearAnalysis,
    fetchDatasets,
  } = useDatasetStore();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [files, setFiles] = useState<File[]>([]);
  const [mapping, setMapping] = useState<FieldMapping>({
    question_field: '',
    answer_field: '',
  });
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [mergeMode, setMergeMode] = useState<MergeMode>('single');
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dirInputRef = useRef<HTMLInputElement>(null);
  const nameWasAutoSet = useRef(false);
  const [lastSeenAnalysisId, setLastSeenAnalysisId] = useState<string | null>(null);

  // Adjust mapping state when analysisResult changes (React-approved derived state pattern)
  const currentAnalysisId = analysisResult?.analysis_id ?? null;
  if (currentAnalysisId !== lastSeenAnalysisId) {
    setLastSeenAnalysisId(currentAnalysisId);
    if (analysisResult) {
      const derived = deriveMappingFromAnalysis(analysisResult);
      setMapping(derived);
    }
  }

  const resetState = useCallback(() => {
    setStep(1);
    setFiles([]);
    setMapping({ question_field: '', answer_field: '' });
    setName('');
    setDescription('');
    setTags('');
    setMergeMode('single');
    setDragOver(false);
    setLastSeenAnalysisId(null);
    nameWasAutoSet.current = false;
  }, []);

  const isValidExtension = useCallback((filename: string): boolean => {
    const ext = filename.toLowerCase().split('.').pop();
    return ['yaml', 'yml', 'jsonl', 'ndjson', 'json', 'csv', 'tsv'].includes(ext ?? '');
  }, []);

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const fileArray = Array.from(newFiles).filter((f) => isValidExtension(f.name));
      if (fileArray.length === 0) return;

      setFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name));
        const unique = fileArray.filter((f) => !existingNames.has(f.name));
        return [...prev, ...unique];
      });

      // Pre-populate name from first valid file (only once)
      if (!nameWasAutoSet.current) {
        const firstFile = fileArray[0];
        if (firstFile) {
          const baseName = firstFile.name.replace(/\.[^.]+$/, '');
          setName(baseName);
          nameWasAutoSet.current = true;
        }
      }
    },
    [isValidExtension],
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles],
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        addFiles(e.target.files);
        e.target.value = '';
      }
    },
    [addFiles],
  );

  const handleAnalyze = useCallback(async () => {
    try {
      await analyzeFiles(files);
      setStep(2);
    } catch {
      toast.error('Failed to analyze files. Please check the file formats and try again.');
    }
  }, [files, analyzeFiles]);

  const handleImport = useCallback(async () => {
    if (!analysisResult) return;

    try {
      await smartImport({
        analysis_id: analysisResult.analysis_id,
        name,
        description: description || undefined,
        tags: tags
          ? tags
              .split(',')
              .map((t) => t.trim())
              .filter(Boolean)
          : undefined,
        mapping,
        merge_mode: mergeMode,
      });
      toast.success('Dataset imported successfully');
      fetchDatasets();
      resetState();
      onOpenChange(false);
    } catch {
      toast.error('Failed to import dataset');
    }
  }, [
    analysisResult,
    name,
    description,
    tags,
    mapping,
    mergeMode,
    smartImport,
    fetchDatasets,
    resetState,
    onOpenChange,
  ]);

  const handleClose = useCallback(() => {
    if (analysisResult) {
      clearAnalysis();
    }
    resetState();
    onOpenChange(false);
  }, [analysisResult, clearAnalysis, resetState, onOpenChange]);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        handleClose();
      }
    },
    [handleClose],
  );

  // Compute preview items from sample_rows + current mapping
  const previewItems = useMemo(() => {
    if (!analysisResult?.files?.length) return [];
    const allSamples = analysisResult.files.flatMap((f) => f.sample_rows);
    return allSamples.slice(0, 5).map((row) => ({
      question: mapping.question_field ? String(row[mapping.question_field] ?? '') : '',
      answer:
        mapping.answer_field && mapping.answer_field !== SKIP_VALUE
          ? String(row[mapping.answer_field] ?? '')
          : '',
      metadata: Object.entries(row)
        .filter(([key]) => key !== mapping.question_field && key !== mapping.answer_field)
        .reduce(
          (acc, [key, value]) => {
            acc[key] = value;
            return acc;
          },
          {} as Record<string, unknown>,
        ),
    }));
  }, [analysisResult, mapping]);

  const metadataFields = useMemo(() => {
    if (!analysisResult) return [];
    return analysisResult.merged_fields.filter(
      (f) => f !== mapping.question_field && f !== mapping.answer_field,
    );
  }, [analysisResult, mapping]);

  const STEP_LABELS = ['Upload', 'Map Fields', 'Preview & Confirm'] as const;

  const stepIndicator = (
    <div
      className="flex items-center justify-center gap-2 mb-4"
      data-testid="step-indicator"
      role="group"
      aria-label={`Step ${step} of 3: ${STEP_LABELS[step - 1]}`}
    >
      {[1, 2, 3].map((s) => (
        <div
          key={s}
          role="presentation"
          aria-hidden="true"
          className={`h-2 w-2 rounded-full ${s === step ? 'bg-primary' : 'bg-muted'}`}
        />
      ))}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {step === 1 && 'Import Dataset'}
            {step === 2 && 'Map Fields'}
            {step === 3 && 'Preview & Confirm'}
          </DialogTitle>
          <DialogDescription>
            {step === 1 && 'Upload files or a directory to auto-detect format and fields.'}
            {step === 2 && 'Review detected fields and adjust mapping as needed.'}
            {step === 3 && 'Review the preview and confirm import.'}
          </DialogDescription>
        </DialogHeader>

        {stepIndicator}

        {/* Step 1: Upload */}
        {step === 1 && (
          <div className="space-y-4">
            {/* Drag and drop zone */}
            <div
              data-testid="drop-zone"
              role="button"
              tabIndex={0}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                dragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/25 hover:border-muted-foreground/50'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
              }}
            >
              <Upload className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
              <p className="text-sm font-medium">Drop files here or click to browse</p>
              <p className="text-xs text-muted-foreground mt-1">
                Supports YAML, JSONL, JSON, CSV, TSV
              </p>
            </div>

            {/* Hidden file inputs */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ACCEPTED_EXTENSIONS}
              onChange={handleFileInputChange}
              className="hidden"
              data-testid="file-input"
            />
            <input
              ref={dirInputRef}
              type="file"
              // @ts-expect-error -- webkitdirectory is a non-standard attribute not in React's HTMLInputElement types
              webkitdirectory=""
              directory=""
              onChange={handleFileInputChange}
              className="hidden"
              data-testid="dir-input"
            />

            {/* Directory upload button */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => dirInputRef.current?.click()}
              data-testid="dir-upload-button"
            >
              <FolderOpen className="mr-2 h-4 w-4" />
              Upload Directory
            </Button>

            {/* File list */}
            {files.length > 0 && (
              <div className="space-y-2" data-testid="file-list">
                <Label>Selected Files ({files.length})</Label>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {files.map((file, idx) => (
                    <div
                      key={`${file.name}-${idx}`}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="truncate">{file.name}</span>
                        <Badge variant="secondary" className="shrink-0">
                          {formatFileSize(file.size)}
                        </Badge>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => removeFile(idx)}
                        aria-label={`Remove ${file.name}`}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Map */}
        {step === 2 && analysisResult && (
          <div className="space-y-4">
            {/* Per-file summary */}
            <div className="space-y-2">
              <Label>Analyzed Files</Label>
              {analysisResult.files.map((fileResult) => (
                <div
                  key={fileResult.filename}
                  className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
                >
                  <span className="truncate font-medium">{fileResult.filename}</span>
                  <Badge variant="secondary">{fileResult.format}</Badge>
                  <span className="text-muted-foreground">{fileResult.total_rows} rows</span>
                  {fileResult.error && (
                    <span className="flex items-center gap-1 text-destructive text-xs">
                      <AlertCircle className="h-3 w-3" />
                      {fileResult.error}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {/* Detected fields */}
            <div className="space-y-2">
              <Label>Detected Fields</Label>
              <div className="flex flex-wrap gap-1">
                {analysisResult.merged_fields.map((field) => (
                  <Badge key={field} variant="outline">
                    {field}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Field mapping */}
            <div className="space-y-3">
              <Label>Field Mapping</Label>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="question-field" className="text-xs">
                    Question field
                  </Label>
                  <Select
                    value={mapping.question_field || undefined}
                    onValueChange={(value) =>
                      setMapping((prev) => ({ ...prev, question_field: value }))
                    }
                  >
                    <SelectTrigger id="question-field" data-testid="question-field-select">
                      <SelectValue placeholder="Select field..." />
                    </SelectTrigger>
                    <SelectContent>
                      {analysisResult.merged_fields.map((field) => (
                        <SelectItem key={field} value={field}>
                          {field}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="answer-field" className="text-xs">
                    Answer field
                  </Label>
                  <Select
                    value={mapping.answer_field || undefined}
                    onValueChange={(value) =>
                      setMapping((prev) => ({ ...prev, answer_field: value }))
                    }
                  >
                    <SelectTrigger id="answer-field" data-testid="answer-field-select">
                      <SelectValue placeholder="Select field..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={SKIP_VALUE}>-- Skip --</SelectItem>
                      {analysisResult.merged_fields.map((field) => (
                        <SelectItem key={field} value={field}>
                          {field}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Metadata fields (derived, read-only) */}
              {metadataFields.length > 0 && (
                <div className="space-y-1">
                  <Label className="text-xs">Metadata fields (auto-assigned)</Label>
                  <div className="flex flex-wrap gap-1">
                    {metadataFields.map((field) => (
                      <Badge key={field} variant="secondary" className="text-xs">
                        {field}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Confidence indicator */}
            <div className="flex items-center gap-2">
              <Label className="text-xs">Mapping Confidence:</Label>
              <Badge
                className={getConfidenceColor(analysisResult.suggested_mapping.confidence)}
                data-testid="confidence-badge"
              >
                {getConfidenceLabel(analysisResult.suggested_mapping.confidence)} (
                {Math.round(analysisResult.suggested_mapping.confidence * 100)}%)
              </Badge>
            </div>

            {/* Merge mode */}
            <div className="space-y-2">
              <Label>Merge Mode</Label>
              <Select value={mergeMode} onValueChange={(v) => setMergeMode(v as MergeMode)}>
                <SelectTrigger data-testid="merge-mode-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">Single dataset (merge all files)</SelectItem>
                  <SelectItem value="separate">Separate dataset per file</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {/* Step 3: Preview & Confirm */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="dataset-name">Name *</Label>
              <Input
                id="dataset-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dataset name"
                data-testid="dataset-name-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="dataset-description">Description</Label>
              <Textarea
                id="dataset-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="dataset-tags">Tags (comma-separated)</Label>
              <Input
                id="dataset-tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="tag1, tag2, tag3"
              />
            </div>

            {/* Preview table */}
            {previewItems.length > 0 && (
              <div className="space-y-2">
                <Label>
                  Preview ({analysisResult?.total_rows ?? 0} total items, showing first{' '}
                  {previewItems.length})
                </Label>
                <div className="rounded-md border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-10">#</TableHead>
                        <TableHead>Question</TableHead>
                        <TableHead>Answer</TableHead>
                        <TableHead>Metadata</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewItems.map((item, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="text-muted-foreground">{idx + 1}</TableCell>
                          <TableCell className="max-w-[200px] truncate">
                            {item.question || '-'}
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate">
                            {item.answer || '-'}
                          </TableCell>
                          <TableCell className="max-w-[150px] truncate text-xs text-muted-foreground">
                            {Object.keys(item.metadata).length > 0
                              ? JSON.stringify(item.metadata)
                              : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        )}

        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            {step > 1 && (
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep((s) => (s > 1 ? ((s - 1) as 1 | 2 | 3) : s))}
                data-testid="back-button"
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                Back
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            {step === 1 && (
              <Button
                type="button"
                disabled={files.length === 0 || isAnalyzing}
                onClick={handleAnalyze}
                data-testid="analyze-button"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze'
                )}
              </Button>
            )}
            {step === 2 && (
              <Button
                type="button"
                disabled={!mapping.question_field}
                onClick={() => setStep(3)}
                data-testid="next-button"
              >
                Next
              </Button>
            )}
            {step === 3 && (
              <Button
                type="button"
                disabled={!name.trim() || isImporting}
                onClick={handleImport}
                data-testid="import-button"
              >
                {isImporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  'Import'
                )}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
