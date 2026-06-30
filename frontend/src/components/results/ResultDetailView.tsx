import { useMemo, useRef, useState, Fragment } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getExpandedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ExpandedState,
} from '@tanstack/react-table';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileDown,
  Loader2,
  Pencil,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ChunkDisplay } from '@/components/evaluation/ChunkDisplay';
import { ArenaLeaderboard } from '@/components/evaluation/ArenaLeaderboard';
import { ScoreDistributionChart } from './ScoreDistributionChart';
import { PassFailChart } from './PassFailChart';
import { ContestantScoreChart } from './ContestantScoreChart';
import { RadarComparisonChart } from './RadarComparisonChart';
import { ResultEditSheet } from './ResultEditSheet';
import { DeleteConfirmDialog } from '@/components/ui/delete-confirm-dialog';
import { useResultStore } from '@/stores/resultStore';
import { exportResultsPdf, type PdfExportData } from '@/lib/exportPdf';
import type { Result, AggregateMetrics, DatasetItem, ArenaLeaderboardResponse } from '@/types';

interface PaginationInfo {
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface ResultDetailViewProps {
  results: Result[];
  aggregateMetrics?: AggregateMetrics | null;
  evaluationName?: string;
  evaluationMode?: string;
  datasetItems?: DatasetItem[];
  arenaLeaderboard?: ArenaLeaderboardResponse | null;
  pagination?: PaginationInfo | null;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  onFetchAllForExport?: () => Promise<Result[]>;
}

function ScoreBreakdownBadges({
  breakdown,
}: {
  breakdown: Record<string, number> | null | undefined;
}) {
  const entries = Object.entries(breakdown ?? {});
  if (entries.length === 0) {
    return <span className="text-muted-foreground">--</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([key, value]) => (
        <Badge key={key} variant="outline" className="text-xs">
          {key}: {value.toFixed(2)}
        </Badge>
      ))}
    </div>
  );
}

function ExpandableText({
  text,
  maxLength,
  forceExpand,
}: {
  text: string | null | undefined;
  maxLength: number;
  forceExpand?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const content = text ?? '';

  if (content.length === 0) {
    return <span className="text-muted-foreground">--</span>;
  }

  const showFull = expanded || forceExpand || content.length <= maxLength;

  return (
    <span className="text-sm whitespace-pre-line">
      {showFull ? content : `${content.slice(0, maxLength)}...`}
      {!showFull && (
        <button
          className="ml-1 text-primary underline text-xs whitespace-nowrap"
          data-no-print
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(true);
          }}
        >
          more
        </button>
      )}
      {expanded && !forceExpand && (
        <button
          className="ml-1 text-primary underline text-xs whitespace-nowrap"
          data-no-print
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(false);
          }}
        >
          less
        </button>
      )}
    </span>
  );
}

const EMPTY_METRICS: AggregateMetrics = {
  total_items: 0,
  passed_items: 0,
  failed_items: 0,
  mean_score: 0,
  median_score: 0,
  pass_rate: 0,
  score_distribution: [],
};

// --- Column definitions ---

const expanderColumn: ColumnDef<Result> = {
  id: 'expander',
  header: () => null,
  cell: ({ row }) => (
    <button
      type="button"
      data-no-print
      onClick={(e) => {
        e.stopPropagation();
        row.toggleExpanded();
      }}
      className="p-1"
      aria-label={row.getIsExpanded() ? 'Collapse row' : 'Expand row'}
    >
      {row.getIsExpanded() ? (
        <ChevronDown className="size-4" />
      ) : (
        <ChevronRight className="size-4" />
      )}
    </button>
  ),
  size: 32,
};

const scoreColumn: ColumnDef<Result> = {
  id: 'score',
  header: 'Score',
  accessorFn: (row) => row.score ?? 0,
  cell: ({ getValue }) => (
    <span className="text-right tabular-nums">{(getValue<number>() * 100).toFixed(0)}%</span>
  ),
  enableSorting: true,
};

const passFailColumn: ColumnDef<Result> = {
  id: 'pass',
  header: 'Pass/Fail',
  accessorFn: (row) => row.passed,
  cell: ({ getValue }) => {
    const val = getValue<boolean | null>();
    if (val === true) {
      return (
        <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
          Pass
        </Badge>
      );
    }
    if (val === false) {
      return <Badge variant="destructive">Fail</Badge>;
    }
    return <span className="text-muted-foreground">--</span>;
  },
};

const breakdownColumn: ColumnDef<Result> = {
  id: 'breakdown',
  header: 'Breakdown',
  cell: ({ row }) => <ScoreBreakdownBadges breakdown={row.original.scores_breakdown} />,
};

const reasoningColumn: ColumnDef<Result> = {
  id: 'reasoning',
  header: 'Judge Reasoning',
  cell: ({ row }) => <ExpandableText text={row.original.judge_reasoning} maxLength={100} />,
};

const contestantColumn: ColumnDef<Result> = {
  id: 'contestant',
  header: 'Contestant Model',
  accessorFn: (row) => row.contestant_model ?? '--',
  cell: ({ getValue }) => <span className="font-mono text-sm">{getValue<string>()}</span>,
};

const chunksColumn: ColumnDef<Result> = {
  id: 'chunks',
  header: 'Chunks',
  accessorFn: (row) => row.retrieved_chunks?.length ?? 0,
  cell: ({ getValue }) => {
    const count = getValue<number>();
    return count > 0 ? (
      <Badge variant="outline">{count}</Badge>
    ) : (
      <span className="text-muted-foreground">--</span>
    );
  },
};

// --- Expanded row detail ---

function ExpandedDetail({
  result,
  datasetItem,
  evaluationMode,
  forceExpand,
}: {
  result: Result;
  datasetItem?: DatasetItem;
  evaluationMode?: string;
  forceExpand?: boolean;
}) {
  const isQA = evaluationMode === 'qa';
  const isRAG = evaluationMode === 'rag';
  const showExpected = isQA || isRAG;

  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="font-medium">Question</p>
        <ExpandableText
          text={datasetItem?.question ?? result.dataset_item_id ?? null}
          maxLength={500}
          forceExpand={forceExpand}
        />
      </div>

      {showExpected && (
        <div>
          <p className="font-medium">Expected Answer</p>
          <ExpandableText
            text={datasetItem?.expected_answer ?? null}
            maxLength={500}
            forceExpand={forceExpand}
          />
        </div>
      )}

      <div>
        <p className="font-medium">Actual Answer</p>
        <ExpandableText text={result.actual_answer} maxLength={500} forceExpand={forceExpand} />
      </div>

      {isRAG && result.retrieved_chunks && result.retrieved_chunks.length > 0 && (
        <div>
          <p className="font-medium mb-2">Retrieved Chunks</p>
          <ChunkDisplay chunks={result.retrieved_chunks} />
        </div>
      )}

      {result.scores_breakdown && Object.keys(result.scores_breakdown).length > 0 && (
        <div>
          <p className="font-medium mb-1">Metric Breakdown</p>
          <ul className="list-disc list-inside text-muted-foreground">
            {Object.entries(result.scores_breakdown).map(([name, value]) => (
              <li key={name}>
                {name}: {value.toFixed(3)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.judge_reasoning && (
        <div>
          <p className="font-medium">Judge Reasoning</p>
          <blockquote className="mt-1 border-l-2 border-muted-foreground/30 pl-3 text-muted-foreground italic whitespace-pre-line">
            {result.judge_reasoning}
          </blockquote>
        </div>
      )}
    </div>
  );
}

export function ResultDetailView({
  results,
  aggregateMetrics,
  evaluationName,
  evaluationMode,
  datasetItems,
  arenaLeaderboard,
  pagination,
  onPageChange,
  onPageSizeChange,
  onFetchAllForExport,
}: ResultDetailViewProps) {
  const metrics = aggregateMetrics ?? EMPTY_METRICS;
  const [sorting, setSorting] = useState<SortingState>([]);
  const [expanded, setExpanded] = useState<ExpandedState>({});
  const [isExporting, setIsExporting] = useState(false);
  const chartsRef = useRef<HTMLDivElement>(null);
  const [editTarget, setEditTarget] = useState<Result | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Result | null>(null);
  const deleteResult = useResultStore((s) => s.deleteResult);

  const handleExportPdf = async () => {
    setIsExporting(true);
    try {
      // If paginated, fetch all results before generating PDF
      let exportResults = results;
      if (onFetchAllForExport && pagination && pagination.pages > 1) {
        toast.info('Fetching all results for export...');
        exportResults = await onFetchAllForExport();
      }

      const chartElements: HTMLElement[] = [];
      if (chartsRef.current) {
        chartsRef.current.querySelectorAll<HTMLElement>('[data-chart]').forEach((el) => {
          chartElements.push(el);
        });
      }

      const pdfData: PdfExportData = {
        evaluationName: evaluationName ?? 'Evaluation',
        evaluationMode: evaluationMode ?? 'qa',
        metrics: {
          totalItems: metrics.total_items || exportResults.length,
          passRate: metrics.pass_rate,
          meanScore: metrics.mean_score,
          medianScore: metrics.median_score,
          passedItems: metrics.passed_items,
          failedItems: metrics.failed_items,
        },
        results: exportResults.map((r) => {
          const item = r.dataset_item_id ? itemMap.get(r.dataset_item_id) : undefined;
          return {
            question: item?.question ?? r.dataset_item_id ?? '--',
            expectedAnswer: item?.expected_answer,
            actualAnswer: r.actual_answer,
            score: r.score,
            passed: r.passed,
            judgeReasoning: r.judge_reasoning,
            scoresBreakdown: r.scores_breakdown,
            contestantModel: r.contestant_model,
          };
        }),
        chartElements,
      };

      await exportResultsPdf(pdfData);
    } catch {
      toast.error('Failed to export PDF. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const itemMap = useMemo(() => {
    const map = new Map<string, DatasetItem>();
    datasetItems?.forEach((item) => map.set(item.id, item));
    return map;
  }, [datasetItems]);

  // Build question column with access to itemMap
  const questionColumn: ColumnDef<Result> = useMemo(
    () => ({
      id: 'question',
      header: 'Question',
      accessorFn: (row) => {
        const item = row.dataset_item_id ? itemMap.get(row.dataset_item_id) : undefined;
        return item?.question ?? row.dataset_item_id ?? '--';
      },
      cell: ({ getValue }) => (
        <span className="block max-w-[250px] truncate" title={getValue<string>()}>
          {getValue<string>()}
        </span>
      ),
    }),
    [itemMap],
  );

  const actionsColumn: ColumnDef<Result> = useMemo(
    () => ({
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Edit result"
            onClick={(e) => {
              e.stopPropagation();
              setEditTarget(row.original);
            }}
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Delete result"
            onClick={(e) => {
              e.stopPropagation();
              setDeleteTarget(row.original);
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
      size: 80,
    }),
    [],
  );

  const columns = useMemo<ColumnDef<Result>[]>(() => {
    switch (evaluationMode) {
      case 'qa':
        return [expanderColumn, questionColumn, scoreColumn, passFailColumn, actionsColumn];
      case 'rag':
        return [
          expanderColumn,
          questionColumn,
          chunksColumn,
          scoreColumn,
          passFailColumn,
          actionsColumn,
        ];
      case 'arena':
        return [
          expanderColumn,
          contestantColumn,
          questionColumn,
          scoreColumn,
          passFailColumn,
          actionsColumn,
        ];
      case 'agent':
        return [scoreColumn, passFailColumn, breakdownColumn, reasoningColumn, actionsColumn];
      default:
        return [scoreColumn, passFailColumn, breakdownColumn, reasoningColumn, actionsColumn];
    }
  }, [evaluationMode, questionColumn, actionsColumn]);

  const isExpandable =
    evaluationMode === 'qa' || evaluationMode === 'rag' || evaluationMode === 'arena';

  const table = useReactTable({
    data: results,
    columns,
    state: { sorting, expanded },
    onSortingChange: setSorting,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: () => isExpandable,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between" data-no-print>
        <Link
          to="/results"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          data-no-print
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Results
        </Link>
        <Button
          variant="outline"
          size="sm"
          disabled={isExporting}
          onClick={() => void handleExportPdf()}
        >
          {isExporting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <FileDown className="h-4 w-4" />
          )}
          Export PDF
        </Button>
      </div>

      {/* Summary Header — arena gets leaderboard + charts, others get aggregate metrics */}
      {evaluationMode === 'arena' && arenaLeaderboard ? (
        <>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <ArenaLeaderboard leaderboard={arenaLeaderboard} />
            <ContestantScoreChart contestants={arenaLeaderboard.contestants} />
          </div>
          {arenaLeaderboard.contestants.some(
            (c) => c.average_breakdown && Object.keys(c.average_breakdown).length >= 2,
          ) && (
            <RadarComparisonChart
              series={arenaLeaderboard.contestants
                .filter((c) => c.average_breakdown)
                .map((c) => ({ name: c.contestant_model, data: c.average_breakdown! }))}
              title="Per-Metric Comparison"
            />
          )}
        </>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                {evaluationName ?? 'Evaluation Result'}
                {evaluationMode && (
                  <Badge variant="outline" className="text-xs">
                    {evaluationMode.toUpperCase()}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Items</p>
                  <p className="text-2xl font-bold">{metrics.total_items || results.length}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Pass Rate</p>
                  <p className="text-2xl font-bold">{(metrics.pass_rate * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Mean Score</p>
                  <p className="text-2xl font-bold">{metrics.mean_score.toFixed(3)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Median Score</p>
                  <p className="text-2xl font-bold">{metrics.median_score.toFixed(3)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2" ref={chartsRef}>
            <div data-chart>
              <ScoreDistributionChart distribution={metrics.score_distribution} />
            </div>
            <div data-chart>
              <PassFailChart
                passedItems={metrics.passed_items}
                failedItems={metrics.failed_items}
              />
            </div>
          </div>
        </>
      )}

      {/* RAG metrics radar */}
      {evaluationMode === 'rag' &&
        (() => {
          const allBreakdowns = results
            .map((r) => r.scores_breakdown)
            .filter((b): b is Record<string, number> => b != null && Object.keys(b).length > 0);

          if (allBreakdowns.length === 0) return null;

          const allKeys = new Set<string>();
          allBreakdowns.forEach((b) => Object.keys(b).forEach((k) => allKeys.add(k)));

          if (allKeys.size < 2) return null;

          const avgData: Record<string, number> = {};
          for (const key of allKeys) {
            const values = allBreakdowns.filter((b) => key in b).map((b) => b[key] ?? 0);
            avgData[key] =
              values.length > 0
                ? values.reduce((a, c) => (a ?? 0) + (c ?? 0), 0) / values.length
                : 0;
          }

          return (
            <RadarComparisonChart
              series={[{ name: 'Average', data: avgData }]}
              title="RAG Metrics Profile"
            />
          );
        })()}

      {/* Per-Item Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Per-Item Results</CardTitle>
        </CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <p className="text-muted-foreground py-4 text-center">
              No individual results available.
            </p>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <TableHead key={header.id}>
                          {header.isPlaceholder
                            ? null
                            : flexRender(header.column.columnDef.header, header.getContext())}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>
                <TableBody>
                  {table.getRowModel().rows.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={columns.length}
                        className="text-center text-muted-foreground"
                      >
                        No results to display.
                      </TableCell>
                    </TableRow>
                  ) : (
                    table.getRowModel().rows.map((row) => (
                      <Fragment key={row.id}>
                        <TableRow
                          className={isExpandable ? 'cursor-pointer' : undefined}
                          onClick={() => {
                            if (isExpandable) row.toggleExpanded();
                          }}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id}>
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </TableCell>
                          ))}
                        </TableRow>
                        {row.getIsExpanded() && (
                          <TableRow>
                            <TableCell colSpan={columns.length} className="bg-muted/30 p-4">
                              <ExpandedDetail
                                result={row.original}
                                datasetItem={
                                  row.original.dataset_item_id
                                    ? itemMap.get(row.original.dataset_item_id)
                                    : undefined
                                }
                                evaluationMode={evaluationMode}
                                forceExpand={isExporting}
                              />
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit / Delete dialogs */}
      {editTarget && (
        <ResultEditSheet
          open={!!editTarget}
          onOpenChange={(open) => {
            if (!open) setEditTarget(null);
          }}
          result={editTarget}
        />
      )}
      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Delete result"
        description="Are you sure you want to delete this result?"
        entityName={deleteTarget?.name ?? deleteTarget?.id.slice(0, 8) ?? ''}
        onConfirm={async () => {
          if (!deleteTarget) return;
          await deleteResult(deleteTarget.id);
          toast.success('Result deleted');
          setDeleteTarget(null);
        }}
      />

      {/* Pagination controls */}
      {pagination && pagination.pages > 1 && (
        <div className="flex items-center justify-between" data-testid="pagination-controls">
          <p className="text-sm text-muted-foreground">
            Showing {(pagination.page - 1) * pagination.page_size + 1}–
            {Math.min(pagination.page * pagination.page_size, pagination.total)} of{' '}
            {pagination.total} results
          </p>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Per page</span>
              <Select
                value={String(pagination.page_size)}
                onValueChange={(value) => onPageSizeChange?.(Number(value))}
              >
                <SelectTrigger size="sm" className="w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                  <SelectItem value="250">250</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={pagination.page <= 1}
                onClick={() => onPageChange?.(pagination.page - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="px-2 text-sm text-muted-foreground">
                Page {pagination.page} of {pagination.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={pagination.page >= pagination.pages}
                onClick={() => onPageChange?.(pagination.page + 1)}
                aria-label="Next page"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
