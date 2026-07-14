import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { formatBadgeValue } from '@/lib/metadataUtils';
import { cn } from '@/lib/utils';

interface MetadataBadgesProps {
  metadata: Record<string, string> | null | undefined;
  /** Maximum number of inline badges before overflow (default 4). */
  maxInline?: number;
  /** Use smaller styling for list views. */
  compact?: boolean;
  className?: string;
}

export function MetadataBadges({
  metadata,
  maxInline = 4,
  compact = false,
  className,
}: MetadataBadgesProps): React.JSX.Element | null {
  if (!metadata || Object.keys(metadata).length === 0) return null;

  const entries = Object.entries(metadata);
  const visible = entries.slice(0, maxInline);
  const overflow = entries.slice(maxInline);

  const badgeClass = compact
    ? 'text-[10px] px-1.5 py-0 h-[18px]'
    : 'text-[11px] px-2 py-0.5 h-5';

  return (
    <div className={cn('flex flex-wrap items-center gap-1', className)}>
      {visible.map(([key, value]) => (
        <Badge key={key} variant="outline" className={cn(badgeClass, 'font-normal')}>
          {key}: {formatBadgeValue(value)}
        </Badge>
      ))}
      {overflow.length > 0 && (
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge variant="secondary" className={cn(badgeClass, 'cursor-default font-normal')}>
                +{overflow.length} more
              </Badge>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              <div className="space-y-0.5">
                {overflow.map(([key, value]) => (
                  <div key={key} className="text-xs">
                    {key}: {value}
                  </div>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}
