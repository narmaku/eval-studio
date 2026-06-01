import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ChunkDisplay } from './ChunkDisplay';
import type { Result, DatasetItem } from '@/types';

interface RAGResultDetailDrawerProps {
  result: Result | null;
  datasetItem?: DatasetItem;
  open: boolean;
  onClose: () => void;
}

export function RAGResultDetailDrawer({
  result,
  datasetItem,
  open,
  onClose,
}: RAGResultDetailDrawerProps) {
  if (!result) return null;

  const breakdown = result.scores_breakdown ?? {};
  const hasBreakdown = Object.keys(breakdown).length > 0;
  const chunks = result.retrieved_chunks ?? [];

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>RAG Result Detail</SheetTitle>
          <SheetDescription>
            Item:{' '}
            {datasetItem?.question
              ? datasetItem.question.slice(0, 60)
              : (result.dataset_item_id?.slice(0, 8) ?? '--')}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 p-4">
          {/* Score + Pass/Fail */}
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold tabular-nums">
              {result.score != null ? `${(result.score * 100).toFixed(0)}%` : '--'}
            </span>
            {result.passed === true ? (
              <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                Pass
              </Badge>
            ) : result.passed === false ? (
              <Badge variant="destructive">Fail</Badge>
            ) : null}
          </div>

          <Separator />

          {/* Question */}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">Question</h3>
            <p className="text-sm text-muted-foreground">{datasetItem?.question ?? '--'}</p>
          </div>

          <Separator />

          {/* Expected Answer */}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">Expected Answer</h3>
            <p className="text-sm text-muted-foreground">{datasetItem?.expected_answer ?? 'N/A'}</p>
          </div>

          <Separator />

          {/* Retrieved Chunks */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Retrieved Chunks ({chunks.length})</h3>
            <ChunkDisplay chunks={chunks} />
          </div>

          <Separator />

          {/* Actual Answer */}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">Actual Answer</h3>
            <p className="text-sm text-muted-foreground">{result.actual_answer || 'N/A'}</p>
          </div>

          <Separator />

          {/* Score Breakdown */}
          {hasBreakdown && (
            <>
              <div className="space-y-1">
                <h3 className="text-sm font-medium">Per-Metric Scores</h3>
                <ul className="space-y-1">
                  {Object.entries(breakdown).map(([name, value]) => (
                    <li key={name} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">{name}</span>
                      <span className="tabular-nums">{(value * 100).toFixed(0)}%</span>
                    </li>
                  ))}
                </ul>
              </div>
              <Separator />
            </>
          )}

          {/* Judge Reasoning */}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">Judge Reasoning</h3>
            <blockquote className="border-l-2 border-muted-foreground/30 pl-3 text-sm text-muted-foreground italic">
              {result.judge_reasoning || 'No reasoning provided.'}
            </blockquote>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
