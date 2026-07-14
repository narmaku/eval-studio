import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MetadataBadges } from '@/components/ui/MetadataBadges';
import { cn } from '@/lib/utils';
import {
  getModeBadgeClasses,
  getModeLabel,
  getStatusPillClasses,
  formatMonoTimestamp,
} from '@/lib/designUtils';
import { Info } from 'lucide-react';
import type { Session } from '@/types';

interface SessionInfoCardProps {
  session: Session;
  messageCount: number;
  metadata: Record<string, string>;
}

export function SessionInfoCard({
  session,
  messageCount,
  metadata,
}: SessionInfoCardProps): React.JSX.Element {
  const hasMetadata = Object.keys(metadata).length > 0;
  const hasTags = session.tags && session.tags.length > 0;

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Info className="h-4 w-4" />
          Session Details
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 space-y-3 pt-4">
        {/* Mode + Status */}
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'rounded-[6px] px-2 py-0.5 text-[10px] font-semibold uppercase',
              getModeBadgeClasses(session.mode),
            )}
          >
            {getModeLabel(session.mode)}
          </span>
          <span
            className={cn(
              'rounded-full px-2.5 py-0.5 text-[10.5px] font-medium capitalize',
              getStatusPillClasses(session.status),
            )}
          >
            {session.status}
          </span>
        </div>

        {/* Timestamps + message count */}
        <div className="space-y-1">
          <div className="flex items-center gap-4 font-mono text-[11px] text-text-2">
            <span>Started: {formatMonoTimestamp(session.started_at ?? session.created_at)}</span>
          </div>
          {session.ended_at && (
            <div className="font-mono text-[11px] text-text-2">
              Ended: {formatMonoTimestamp(session.ended_at)}
            </div>
          )}
          <div className="font-mono text-[11px] text-text-2">{messageCount} messages</div>
        </div>

        {/* Tags */}
        {hasTags && (
          <div className="flex flex-wrap items-center gap-1">
            {session.tags!.map((tag) => (
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
        {hasMetadata && <MetadataBadges metadata={metadata} maxInline={6} />}
      </CardContent>
    </Card>
  );
}
