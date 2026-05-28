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
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useRubricStore } from '@/stores/rubricStore';
import { api } from '@/services/api';
import type { Provider, Rubric } from '@/types';

interface RubricRefineDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rubric: Rubric;
  onRefined?: () => void;
}

export function RubricRefineDialog({
  open,
  onOpenChange,
  rubric,
  onRefined,
}: RubricRefineDialogProps) {
  const refineRubric = useRubricStore((s) => s.refineRubric);

  const [feedback, setFeedback] = useState('');
  const [providerId, setProviderId] = useState('');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      api.listProviders().then(setProviders).catch(() => {});
    }
  }, [open]);

  const handleRefine = async () => {
    if (!feedback.trim() || !providerId) return;
    setIsLoading(true);
    setError(null);
    try {
      await refineRubric(rubric.id, {
        feedback,
        provider_id: providerId,
      });
      setFeedback('');
      setProviderId('');
      onRefined?.();
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Refinement failed';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setFeedback('');
      setError(null);
    }
    onOpenChange(nextOpen);
  };

  const canRefine = feedback.trim().length > 0 && providerId.length > 0 && !isLoading;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Refine Rubric</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="font-medium">{rubric.name}</span>
            <Badge variant="secondary">
              {rubric.dimensions.length}{' '}
              {rubric.dimensions.length === 1 ? 'dimension' : 'dimensions'}
            </Badge>
          </div>

          <div className="space-y-2">
            <Label htmlFor="refine-feedback">Feedback</Label>
            <Textarea
              id="refine-feedback"
              placeholder="What should be improved about this rubric?"
              value={feedback}
              onChange={(e) => {
                setFeedback(e.target.value);
                setError(null);
              }}
              rows={4}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="refine-provider">Provider</Label>
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
              Refining rubric... This may take 10-30 seconds.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleRefine} disabled={!canRefine}>
            {isLoading ? 'Refining...' : 'Refine'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
