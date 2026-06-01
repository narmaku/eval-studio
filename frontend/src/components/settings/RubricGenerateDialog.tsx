import { useEffect, useState } from 'react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useRubricStore } from '@/stores/rubricStore';
import { api } from '@/services/api';
import type { Provider } from '@/types';

interface RubricGenerateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerated?: () => void;
}

export function RubricGenerateDialog({
  open,
  onOpenChange,
  onGenerated,
}: RubricGenerateDialogProps) {
  const generateRubric = useRubricStore((s) => s.generateRubric);

  const [description, setDescription] = useState('');
  const [sampleData, setSampleData] = useState('');
  const [providerId, setProviderId] = useState('');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      api
        .listProviders()
        .then(setProviders)
        .catch(() => {});
    }
  }, [open]);

  const handleGenerate = async () => {
    if (!description.trim() || !providerId) return;
    setIsLoading(true);
    setError(null);
    try {
      await generateRubric({
        description,
        ...(sampleData.trim() ? { sample_data: sampleData } : {}),
        provider_id: providerId,
      });
      setDescription('');
      setSampleData('');
      setProviderId('');
      onGenerated?.();
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Generation failed';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setDescription('');
      setSampleData('');
      setError(null);
    }
    onOpenChange(nextOpen);
  };

  const canGenerate = description.trim().length > 0 && providerId.length > 0 && !isLoading;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Generate Rubric</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="gen-description">Description</Label>
            <Textarea
              id="gen-description"
              placeholder="Describe what you want to evaluate..."
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                setError(null);
              }}
              rows={4}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="gen-sample-data">Sample data (optional)</Label>
            <Textarea
              id="gen-sample-data"
              placeholder="Paste sample Q&A pairs or chat data for context..."
              value={sampleData}
              onChange={(e) => setSampleData(e.target.value)}
              rows={4}
              className="font-mono text-sm"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="gen-provider">Provider</Label>
            <Select value={providerId} onValueChange={setProviderId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a provider..." />
              </SelectTrigger>
              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          {isLoading && (
            <p className="text-sm text-muted-foreground">
              Generating rubric... This may take 10-30 seconds.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} disabled={!canGenerate}>
            {isLoading ? 'Generating...' : 'Generate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
