import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { extractContestantSpecs, getSpecsDiff } from '@/lib/metadataUtils';
import { cn } from '@/lib/utils';
import type { EvaluationConfig } from '@/types';

interface ContestantSpecsCardProps {
  config: EvaluationConfig;
  className?: string;
}

export function ContestantSpecsCard({
  config,
  className,
}: ContestantSpecsCardProps): React.JSX.Element | null {
  const specs = useMemo(() => extractContestantSpecs(config), [config]);
  const diff = useMemo(() => getSpecsDiff(specs), [specs]);

  if (specs.length === 0) return null;

  const hasMatching = Object.keys(diff.matching).length > 0;
  const hasDifferences = diff.unmatching.length > 0;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Contestant Specs</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Contestant model names */}
        {!hasDifferences && (
          <div className="flex flex-wrap gap-2">
            {specs.map((spec) => (
              <span
                key={spec.model}
                className="rounded-[6px] bg-surface-3 px-2 py-0.5 text-xs font-mono font-medium"
              >
                {spec.model}
              </span>
            ))}
          </div>
        )}

        {/* Differences table */}
        {hasDifferences && (
          <div>
            <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-text-3">
              Differences
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px] text-xs">Field</TableHead>
                  {specs.map((spec) => (
                    <TableHead key={spec.model} className="text-xs font-medium">
                      {spec.model}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {diff.unmatching.map(({ key, values }) => (
                  <TableRow key={key}>
                    <TableCell className="text-xs font-medium text-text-2">{key}</TableCell>
                    {values.map((val, i) => {
                      // Highlight cells that differ from the first value
                      const differs = val !== values[0];
                      return (
                        <TableCell
                          key={i}
                          className={cn(
                            'text-xs font-mono',
                            differs && 'bg-amber-50 dark:bg-amber-950/20',
                          )}
                        >
                          {val ?? <span className="text-text-3 italic">--</span>}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Shared fields */}
        {hasMatching && (
          <div>
            <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-text-3">
              Shared
            </p>
            <div className="space-y-1">
              {Object.entries(diff.matching).map(([key, value]) => (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-text-2">{key}:</span>
                  <span className="font-mono text-text-1">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
