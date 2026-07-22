import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MetadataBadges } from '@/components/ui/MetadataBadges';
import { cn } from '@/lib/utils';
import {
  getModeBadgeClasses,
  getModeLabel,
  getStatusPillClasses,
  formatMonoTimestamp,
} from '@/lib/designUtils';
import { extractConfigMetadata, mergeMetadata, filterSensitiveKeys } from '@/lib/metadataUtils';
import { Info, RotateCcw } from 'lucide-react';
import type { Evaluation } from '@/types';

interface EvaluationInfoCardProps {
  evaluation: Evaluation;
  className?: string;
}

export function EvaluationInfoCard({
  evaluation,
  className,
}: EvaluationInfoCardProps): React.JSX.Element {
  const configMeta = evaluation.config
    ? filterSensitiveKeys(extractConfigMetadata(evaluation.config))
    : {};
  const merged = mergeMetadata(configMeta, evaluation.metadata);
  const hasMetadata = Object.keys(merged).length > 0;
  const hasTags = evaluation.tags && evaluation.tags.length > 0;
  const isRerun = evaluation.metadata?.is_rerun === 'true';

  return (
    <Card className={cn('flex h-full flex-col overflow-hidden', className)}>
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Info className="h-4 w-4" />
          Evaluation Details
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 space-y-3 pt-4">
        {/* Mode + Status */}
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'rounded-[6px] px-2 py-0.5 text-[10px] font-semibold uppercase',
              getModeBadgeClasses(evaluation.mode),
            )}
          >
            {getModeLabel(evaluation.mode)}
          </span>
          <span
            className={cn(
              'rounded-full px-2.5 py-0.5 text-[10.5px] font-medium capitalize',
              getStatusPillClasses(evaluation.status),
            )}
          >
            {evaluation.status}
          </span>
        </div>

        {/* Description */}
        {evaluation.description && (
          <p className="text-[12.5px] leading-relaxed text-text-2">{evaluation.description}</p>
        )}

        {/* Re-run lineage */}
        {isRerun && (
          <div className="flex items-center gap-1.5 rounded-[8px] bg-surface-2 px-2.5 py-1.5 text-[11px] text-text-2">
            <RotateCcw className="h-3 w-3 shrink-0" />
            <span>
              Re-run of:{' '}
              <span className="font-medium">{evaluation.metadata?.original_run_name}</span>
            </span>
          </div>
        )}

        {/* Timestamps + item count */}
        <div className="space-y-1">
          <div className="font-mono text-[11px] text-text-2">
            Created: {formatMonoTimestamp(evaluation.created_at)}
          </div>
          {evaluation.updated_at && evaluation.updated_at !== evaluation.created_at && (
            <div className="font-mono text-[11px] text-text-2">
              Updated: {formatMonoTimestamp(evaluation.updated_at)}
            </div>
          )}
          {evaluation.result_count != null && evaluation.result_count > 0 && (
            <div className="font-mono text-[11px] text-text-2">
              {evaluation.result_count} items scored
            </div>
          )}
        </div>

        {/* Tags */}
        {hasTags && (
          <div className="flex flex-wrap items-center gap-1">
            {evaluation.tags!.map((tag) => (
              <span
                key={tag}
                className="rounded-[5px] bg-surface-3 px-1.5 py-0.5 text-[10px] text-text-3"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Metadata badges */}
        {hasMetadata && <MetadataBadges metadata={merged} maxInline={6} />}
      </CardContent>
    </Card>
  );
}
