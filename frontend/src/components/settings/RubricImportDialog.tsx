import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useRubricStore } from '@/stores/rubricStore';

interface RubricImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported?: () => void;
}

export function RubricImportDialog({
  open,
  onOpenChange,
  onImported,
}: RubricImportDialogProps) {
  const importRubric = useRubricStore((s) => s.importRubric);

  const [yamlContent, setYamlContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result;
      if (typeof text === 'string') {
        setYamlContent(text);
        setError(null);
      }
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    if (!yamlContent.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      await importRubric({ yaml_content: yamlContent });
      setYamlContent('');
      onImported?.();
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Import failed';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setYamlContent('');
      setError(null);
    }
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Import Rubric</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="yaml-file">Upload YAML file</Label>
            <input
              id="yaml-file"
              type="file"
              accept=".yaml,.yml"
              onChange={handleFileChange}
              className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary-foreground hover:file:bg-primary/90"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="yaml-content">Or paste YAML content</Label>
            <Textarea
              id="yaml-content"
              placeholder="Paste YAML rubric content here..."
              value={yamlContent}
              onChange={(e) => {
                setYamlContent(e.target.value);
                setError(null);
              }}
              rows={10}
              className="font-mono text-sm"
            />
          </div>

          <p className="text-xs text-muted-foreground">
            Import rubric in rubric-kit YAML format. See{' '}
            <a
              href="https://github.com/instructlab/rubric-kit"
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              rubric-kit
            </a>{' '}
            for format reference.
          </p>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={!yamlContent.trim() || isLoading}
          >
            {isLoading ? 'Importing...' : 'Import'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
