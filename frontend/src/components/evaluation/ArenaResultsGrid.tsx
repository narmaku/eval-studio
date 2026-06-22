import { useMemo, useState, useEffect, Fragment } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { api } from '@/services/api';
import type { Result, DatasetItem } from '@/types';

interface ArenaResultsGridProps {
  results: Result[];
  contestants: string[];
  datasetId?: string;
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

function ExpandedArenaDetail({
  group,
  contestants,
  datasetItem,
}: {
  group: GroupedResult;
  contestants: string[];
  datasetItem?: DatasetItem;
}) {
  return (
    <div className="space-y-4 text-sm">
      <div>
        <p className="font-medium">Question</p>
        <p className="text-muted-foreground whitespace-pre-line">
          {datasetItem?.question ?? group.datasetItemId}
        </p>
      </div>
      {datasetItem?.expected_answer && (
        <div>
          <p className="font-medium">Expected Answer</p>
          <p className="text-muted-foreground whitespace-pre-line">{datasetItem.expected_answer}</p>
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {contestants.map((model) => {
          const result = group.byContestant.get(model);
          if (!result) return null;
          return (
            <div key={model} className="rounded-md border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{model}</span>
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
              <div>
                <p className="text-xs font-medium text-muted-foreground">Answer</p>
                <p className="text-sm whitespace-pre-line">{result.actual_answer || '--'}</p>
              </div>
              {result.judge_reasoning && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground">Reasoning</p>
                  <blockquote className="border-l-2 border-muted-foreground/30 pl-2 text-xs text-muted-foreground italic whitespace-pre-line">
                    {result.judge_reasoning}
                  </blockquote>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ArenaResultsGrid({ results, contestants, datasetId }: ArenaResultsGridProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [datasetItems, setDatasetItems] = useState<DatasetItem[]>([]);

  useEffect(() => {
    if (datasetId) {
      api
        .getDataset(datasetId)
        .then((detail) => setDatasetItems(detail.items))
        .catch(() => setDatasetItems([]));
    }
  }, [datasetId]);

  const itemMap = useMemo(() => {
    const map = new Map<string, DatasetItem>();
    datasetItems.forEach((item) => map.set(item.id, item));
    return map;
  }, [datasetItems]);

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

  const toggleRow = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

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
                <TableHead className="w-8" />
                <TableHead className="min-w-[200px]">Question</TableHead>
                {contestants.map((model) => (
                  <TableHead key={model} className="min-w-[150px]">
                    {model}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {grouped.map(({ datasetItemId, byContestant }) => {
                const isExpanded = expandedRows.has(datasetItemId);
                const item = itemMap.get(datasetItemId);
                const questionPreview = item?.question
                  ? truncate(item.question, 60)
                  : truncate(datasetItemId, 12);

                return (
                  <Fragment key={datasetItemId}>
                    <TableRow className="cursor-pointer" onClick={() => toggleRow(datasetItemId)}>
                      <TableCell className="p-1">
                        <button
                          type="button"
                          className="p-1"
                          aria-label={isExpanded ? 'Collapse' : 'Expand'}
                        >
                          {isExpanded ? (
                            <ChevronDown className="size-4" />
                          ) : (
                            <ChevronRight className="size-4" />
                          )}
                        </button>
                      </TableCell>
                      <TableCell className="font-medium text-sm">{questionPreview}</TableCell>
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
                          </TableCell>
                        );
                      })}
                    </TableRow>
                    {isExpanded && (
                      <TableRow>
                        <TableCell colSpan={contestants.length + 2} className="bg-muted/30 p-4">
                          <ExpandedArenaDetail
                            group={{ datasetItemId, byContestant }}
                            contestants={contestants}
                            datasetItem={item}
                          />
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
