import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { Score, DatasetItem } from '@/types';

interface ResultDetailDrawerProps {
  score: Score | null;
  datasetItem?: DatasetItem;
  open: boolean;
  onClose: () => void;
}

export function ResultDetailDrawer({ score, datasetItem, open, onClose }: ResultDetailDrawerProps) {
  if (!score) return null;

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Result Detail</SheetTitle>
          <SheetDescription>
            Item: {datasetItem?.question ? datasetItem.question.slice(0, 60) : score.item_id}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 p-4">
          {/* Score + Pass/Fail */}
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold tabular-nums">
              {(score.overall * 100).toFixed(0)}%
            </span>
            {score.pass ? (
              <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                Pass
              </Badge>
            ) : (
              <Badge variant="destructive">Fail</Badge>
            )}
          </div>

          <Separator />

          {/* Question */}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">Question</h3>
            <p className="text-sm text-muted-foreground">
              {datasetItem?.question ?? score.item_id}
            </p>
          </div>

          <Separator />

          {/* Expected Answer */}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">Expected Answer</h3>
            <p className="text-sm text-muted-foreground">
              {datasetItem?.expected_answer ?? 'N/A'}
            </p>
          </div>

          <Separator />

          {/* Actual Answer */}
          <div className="space-y-1">
            <h3 className="text-sm font-medium">Actual Answer</h3>
            <p className="text-sm text-muted-foreground">{score.raw_response || 'N/A'}</p>
          </div>

          <Separator />

          {/* Per-Dimension Scores */}
          {Object.keys(score.dimensions).length > 0 && (
            <>
              <div className="space-y-1">
                <h3 className="text-sm font-medium">Dimension Scores</h3>
                <ul className="space-y-1">
                  {Object.entries(score.dimensions).map(([name, value]) => (
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
              {score.judge_reasoning || 'No reasoning provided.'}
            </blockquote>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
