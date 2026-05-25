import { useState, useCallback, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import * as yaml from 'yaml';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

import { useDatasetStore } from '@/stores/datasetStore';
import type { DatasetFormat, DatasetItemCreate } from '@/types';

const uploadSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  description: z.string().optional(),
  format: z.enum(['qa_pairs', 'jsonl', 'csv']),
});

type UploadFormData = z.infer<typeof uploadSchema>;

interface DatasetUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const FORMAT_LABELS: Record<DatasetFormat, string> = {
  qa_pairs: 'Q&A Pairs (.yaml)',
  jsonl: 'JSONL (.jsonl)',
  csv: 'CSV (.csv)',
};

const FORMAT_ACCEPT: Record<DatasetFormat, string> = {
  qa_pairs: '.yaml,.yml',
  jsonl: '.jsonl',
  csv: '.csv',
};

function parseYaml(text: string): DatasetItemCreate[] {
  const doc = yaml.parse(text) as { items?: unknown[] };
  if (!doc?.items || !Array.isArray(doc.items)) {
    throw new Error('YAML must contain an "items" array');
  }
  return doc.items.map((item: unknown) => {
    const obj = item as Record<string, unknown>;
    if (typeof obj?.question !== 'string') {
      throw new Error('Each item must have a "question" field');
    }
    return {
      question: obj.question,
      expected_answer: typeof obj.expected_answer === 'string' ? obj.expected_answer : undefined,
      metadata:
        typeof obj.metadata === 'object' && obj.metadata !== null
          ? (obj.metadata as Record<string, unknown>)
          : undefined,
    };
  });
}

function parseJsonl(text: string): DatasetItemCreate[] {
  const lines = text.split('\n').filter((line) => line.trim().length > 0);
  return lines.map((line, idx) => {
    let obj: Record<string, unknown>;
    try {
      obj = JSON.parse(line) as Record<string, unknown>;
    } catch {
      throw new Error(`Invalid JSON on line ${idx + 1}`);
    }
    if (typeof obj.question !== 'string') {
      throw new Error(`Line ${idx + 1} must have a "question" field`);
    }
    return {
      question: obj.question,
      expected_answer: typeof obj.expected_answer === 'string' ? obj.expected_answer : undefined,
      metadata:
        typeof obj.metadata === 'object' && obj.metadata !== null
          ? (obj.metadata as Record<string, unknown>)
          : undefined,
    };
  });
}

function parseCsv(text: string): DatasetItemCreate[] {
  const lines = text.split('\n').filter((line) => line.trim().length > 0);
  if (lines.length < 2) {
    throw new Error('CSV must have a header row and at least one data row');
  }
  const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
  const questionIdx = headers.indexOf('question');
  const answerIdx = headers.indexOf('expected_answer');
  if (questionIdx === -1) {
    throw new Error('CSV header must include a "question" column');
  }
  return lines.slice(1).map((line) => {
    const values = line.split(',').map((v) => v.trim());
    return {
      question: values[questionIdx],
      expected_answer: answerIdx !== -1 ? values[answerIdx] : undefined,
    };
  });
}

export function DatasetUploadDialog({ open, onOpenChange }: DatasetUploadDialogProps) {
  const { uploadDataset } = useDatasetStore();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      name: '',
      description: '',
      format: 'qa_pairs',
    },
  });

  const [parsedItems, setParsedItems] = useState<DatasetItemCreate[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const format = watch('format');
  const name = watch('name');

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      reset();
      setParsedItems([]);
      setParseError(null);
      setIsUploading(false);
    }
  }, [open, reset]);

  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) {
        setParsedItems([]);
        setParseError(null);
        return;
      }

      // File size limit: 10MB
      if (file.size > 10 * 1024 * 1024) {
        setParseError('File size must be under 10MB');
        setParsedItems([]);
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        try {
          let items: DatasetItemCreate[];
          switch (format) {
            case 'qa_pairs':
              items = parseYaml(text);
              break;
            case 'jsonl':
              items = parseJsonl(text);
              break;
            case 'csv':
              items = parseCsv(text);
              break;
            default:
              throw new Error(`Unsupported format: ${format}`);
          }
          if (items.length === 0) {
            throw new Error('File contains no items');
          }
          setParsedItems(items);
          setParseError(null);
        } catch (err) {
          setParseError(err instanceof Error ? err.message : 'Failed to parse file');
          setParsedItems([]);
        }
      };
      reader.readAsText(file);
    },
    [format],
  );

  const onSubmit = async (data: UploadFormData) => {
    setIsUploading(true);
    try {
      await uploadDataset({
        name: data.name,
        description: data.description || undefined,
        format: data.format,
        items: parsedItems,
      });
      toast.success('Dataset uploaded successfully');
      onOpenChange(false);
    } catch {
      toast.error('Failed to upload dataset');
    } finally {
      setIsUploading(false);
    }
  };

  const isSubmitDisabled = !name || parsedItems.length === 0 || isUploading;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Dataset</DialogTitle>
          <DialogDescription>
            Upload a dataset file to create a new evaluation dataset.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="dataset-name" className="text-sm font-medium">
              Name
            </label>
            <Input id="dataset-name" placeholder="My Dataset" {...register('name')} />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="dataset-description" className="text-sm font-medium">
              Description
            </label>
            <Input
              id="dataset-description"
              placeholder="Optional description"
              {...register('description')}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Format</label>
            <Select
              value={format}
              onValueChange={(value: DatasetFormat) => setValue('format', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select format" />
              </SelectTrigger>
              <SelectContent>
                {(Object.entries(FORMAT_LABELS) as [DatasetFormat, string][]).map(
                  ([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label htmlFor="dataset-file" className="text-sm font-medium">
              File
            </label>
            <input
              id="dataset-file"
              type="file"
              accept={FORMAT_ACCEPT[format]}
              onChange={handleFileChange}
              data-testid="file-input"
              className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
            />
            {parseError && <p className="text-sm text-destructive">{parseError}</p>}
          </div>

          {parsedItems.length > 0 && (
            <div className="rounded-md border p-3 space-y-2">
              <p className="text-sm font-medium">
                Parsed {parsedItems.length} item{parsedItems.length !== 1 ? 's' : ''}
              </p>
              <div className="max-h-40 overflow-y-auto space-y-2">
                {parsedItems.slice(0, 3).map((item, idx) => (
                  <div key={idx} className="text-xs space-y-0.5">
                    <p className="font-medium text-foreground">
                      {idx + 1}. {item.question.length > 100 ? `${item.question.slice(0, 100)}...` : item.question}
                    </p>
                    {item.expected_answer && (
                      <p className="text-muted-foreground">
                        A: {item.expected_answer.length > 80 ? `${item.expected_answer.slice(0, 80)}...` : item.expected_answer}
                      </p>
                    )}
                  </div>
                ))}
                {parsedItems.length > 3 && (
                  <p className="text-xs text-muted-foreground">
                    ...and {parsedItems.length - 3} more
                  </p>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitDisabled}>
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                'Upload'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
