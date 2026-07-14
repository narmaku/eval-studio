import { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, AlertTriangle } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { api } from '@/services/api';
import type { EvaluationMode, EvaluationStatus } from '@/types';

type RerunOption = 'full' | 'failures_only' | 'in_place';

interface RerunDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  evaluation: {
    evaluationId: string;
    name: string;
    mode: EvaluationMode;
    totalItems: number;
    passRate: number;
    status: EvaluationStatus;
  };
  onSuccess?: () => void;
}

export function RerunDialog({
  open,
  onOpenChange,
  evaluation,
  onSuccess,
}: RerunDialogProps): React.JSX.Element {
  const [selectedOption, setSelectedOption] = useState<RerunOption>('full');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const failedCount =
    evaluation.totalItems - Math.round(evaluation.totalItems * evaluation.passRate);
  const isArena = evaluation.mode === 'arena';
  const failuresDisabled = isArena || failedCount === 0;

  const handleConfirm = async (): Promise<void> => {
    setIsSubmitting(true);
    try {
      if (selectedOption === 'in_place') {
        await api.rerunEvaluation(evaluation.evaluationId);
        toast.success(`Re-run started in place: "${evaluation.name}"`);
      } else {
        const result = await api.cloneAndRerunEvaluation(evaluation.evaluationId, selectedOption);
        toast.success(`Re-run started: "${result.name}"`);
      }
      onOpenChange(false);
      onSuccess?.();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      toast.error(`Failed to start re-run: ${message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const options: Array<{
    value: RerunOption;
    label: string;
    description: string;
    disabled: boolean;
    disabledReason?: string;
    warning?: string;
  }> = [
    {
      value: 'full',
      label: 'Full re-run (new evaluation)',
      description: `Re-run all ${evaluation.totalItems} items as a new evaluation`,
      disabled: false,
    },
    {
      value: 'failures_only',
      label: 'Re-run failures only (new evaluation)',
      description: failuresDisabled
        ? isArena
          ? 'Not available for arena evaluations'
          : 'No failed items to re-run'
        : `Re-run ${failedCount} of ${evaluation.totalItems} failed items as a new evaluation`,
      disabled: failuresDisabled,
      disabledReason: isArena ? 'Not available for arena mode' : undefined,
    },
    {
      value: 'in_place',
      label: 'Re-run in place (overwrite results)',
      description: 'Re-run all items and replace existing results',
      disabled: false,
      warning: 'This will delete all existing results for this evaluation.',
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Re-run Evaluation</DialogTitle>
          <DialogDescription>
            Choose how to re-run <span className="font-medium">{evaluation.name}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-2">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              disabled={option.disabled || isSubmitting}
              onClick={() => setSelectedOption(option.value)}
              className={`w-full rounded-lg border p-3 text-left transition-colors ${
                selectedOption === option.value
                  ? 'border-primary bg-primary/5 ring-1 ring-primary'
                  : 'border-border hover:border-primary/50'
              } ${option.disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
            >
              <div className="text-sm font-medium">{option.label}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{option.description}</div>
              {option.warning && selectedOption === option.value && (
                <div className="mt-2 flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                  <span>{option.warning}</span>
                </div>
              )}
            </button>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={() => void handleConfirm()} disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Confirm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
