import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { Result } from '@/types';

interface ArenaResultsGridProps {
  results: Result[];
  contestants: string[];
}

function truncate(text: string | null | undefined, maxLength: number): string {
  if (!text) return '--';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

function scoreColorClass(score: number): string {
  if (score >= 0.7) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
  if (score >= 0.4)
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
}

interface GroupedResult {
  datasetItemId: string;
  byContestant: Map<string, Result>;
}

export function ArenaResultsGrid({ results, contestants }: ArenaResultsGridProps) {
  const grouped = useMemo<GroupedResult[]>(() => {
    const map = new Map<string, Map<string, Result>>();

    for (const result of results) {
      const itemId = result.dataset_item_id ?? 'unknown';
      const model = result.contestant_model ?? 'unknown';

      if (!map.has(itemId)) {
        map.set(itemId, new Map());
      }
      map.get(itemId)!.set(model, result);
    }

    return Array.from(map.entries()).map(([datasetItemId, byContestant]) => ({
      datasetItemId,
      byContestant,
    }));
  }, [results]);

  if (results.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Results Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No results to display.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Results Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky left-0 z-10 bg-background min-w-[120px]">
                  Question
                </TableHead>
                {contestants.map((model) => (
                  <TableHead key={model} className="min-w-[200px]">
                    {model}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {grouped.map(({ datasetItemId, byContestant }) => (
                <TableRow key={datasetItemId}>
                  <TableCell className="sticky left-0 z-10 bg-background font-medium">
                    {truncate(datasetItemId, 40)}
                  </TableCell>
                  {contestants.map((model) => {
                    const result = byContestant.get(model);
                    if (!result) {
                      return (
                        <TableCell key={model} className="text-muted-foreground">
                          --
                        </TableCell>
                      );
                    }
                    return (
                      <TableCell key={model}>
                        <div className="space-y-1">
                          <p className="text-sm">{truncate(result.actual_answer, 100)}</p>
                          <div className="flex items-center gap-2">
                            <span
                              className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${scoreColorClass(result.score ?? 0)}`}
                            >
                              {Math.round((result.score ?? 0) * 100)}%
                            </span>
                            {result.passed === true && (
                              <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 text-xs">
                                Pass
                              </Badge>
                            )}
                            {result.passed === false && (
                              <Badge variant="destructive" className="text-xs">
                                Fail
                              </Badge>
                            )}
                          </div>
                        </div>
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
