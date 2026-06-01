import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDownIcon, ChevronRightIcon } from 'lucide-react';
import type { RetrievedChunk } from '@/types';

interface ChunkDisplayProps {
  chunks: RetrievedChunk[];
}

const TRUNCATE_LENGTH = 200;

function getScoreBadgeClasses(score: number | undefined): string {
  if (score === undefined) return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
  if (score > 0.7) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
  if (score > 0.4)
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
}

function ChunkCard({ chunk, index }: { chunk: RetrievedChunk; index: number }) {
  const [isOpen, setIsOpen] = useState(false);
  const needsTruncation = chunk.content.length > TRUNCATE_LENGTH;

  return (
    <Card>
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2">
          <span className="text-xs font-medium text-muted-foreground">Chunk {index + 1}</span>
          <div className="flex items-center gap-2">
            {chunk.source && (
              <span
                className="text-xs text-muted-foreground truncate max-w-[150px]"
                title={chunk.source}
              >
                {chunk.source}
              </span>
            )}
            <Badge
              className={getScoreBadgeClasses(chunk.relevance_score)}
              data-testid={`chunk-score-${index}`}
            >
              {chunk.relevance_score !== undefined
                ? `${(chunk.relevance_score * 100).toFixed(0)}%`
                : 'N/A'}
            </Badge>
          </div>
        </div>

        {needsTruncation ? (
          <Collapsible open={isOpen} onOpenChange={setIsOpen}>
            <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
              {isOpen ? chunk.content : `${chunk.content.slice(0, TRUNCATE_LENGTH)}...`}
            </p>
            <CollapsibleContent />
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="mt-1 flex items-center gap-1 text-xs text-primary hover:underline"
              >
                {isOpen ? (
                  <>
                    <ChevronDownIcon className="size-3" /> Show less
                  </>
                ) : (
                  <>
                    <ChevronRightIcon className="size-3" /> Show more
                  </>
                )}
              </button>
            </CollapsibleTrigger>
          </Collapsible>
        ) : (
          <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">{chunk.content}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function ChunkDisplay({ chunks }: ChunkDisplayProps) {
  if (chunks.length === 0) {
    return <p className="text-sm text-muted-foreground">No chunks retrieved.</p>;
  }

  return (
    <div className="space-y-2">
      {chunks.map((chunk, index) => (
        <ChunkCard key={index} chunk={chunk} index={index} />
      ))}
    </div>
  );
}
