import { useMemo, useState, Fragment } from 'react';
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
import { ArrowLeft, ChevronDown, ChevronRight } from 'lucide-react';
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
import { ChunkDisplay } from '@/components/evaluation/ChunkDisplay';
import { ScoreDistributionChart } from './ScoreDistributionChart';
import { PassFailChart } from './PassFailChart';
import type { Result, AggregateMetrics, DatasetItem } from '@/types';

interface ResultDetailViewProps {
  results: Result[];
  aggregateMetrics?: AggregateMetrics | null;
  evaluationName?: string;
  evaluationMode?: string;
  datasetItems?: DatasetItem[];
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
}: {
  text: string | null | undefined;
  maxLength: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const content = text ?? '';

  if (content.length === 0) {
    return <span className="text-muted-foreground">--</span>;
  }

  if (content.length <= maxLength) {
    return <span className="text-sm whitespace-pre-line">{content}</span>;
  }

  return (
    <span className="text-sm whitespace-pre-line">
      {expanded ? content : `${content.slice(0, maxLength)}...`}
      <button
        className="ml-1 text-primary underline text-xs whitespace-nowrap"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        {expanded ? 'less' : 'more'}
      </button>
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
  score_distribution: {},
};

// --- Column definitions ---

const expanderColumn: ColumnDef<Result> = {
  id: 'expander',
  header: () => null,
  cell: ({ row }) => (
    <button
      type="button"
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
}: {
  result: Result;
  datasetItem?: DatasetItem;
  evaluationMode?: string;
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
        />
      </div>

      {showExpected && (
        <div>
          <p className="font-medium">Expected Answer</p>
          <ExpandableText text={datasetItem?.expected_answer ?? null} maxLength={500} />
        </div>
      )}

      <div>
        <p className="font-medium">Actual Answer</p>
        <ExpandableText text={result.actual_answer} maxLength={500} />
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
}: ResultDetailViewProps) {
  const metrics = aggregateMetrics ?? EMPTY_METRICS;
  const [sorting, setSorting] = useState<SortingState>([]);
  const [expanded, setExpanded] = useState<ExpandedState>({});

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

  const columns = useMemo<ColumnDef<Result>[]>(() => {
    switch (evaluationMode) {
      case 'qa':
        return [expanderColumn, questionColumn, scoreColumn, passFailColumn];
      case 'rag':
        return [expanderColumn, questionColumn, chunksColumn, scoreColumn, passFailColumn];
      case 'arena':
        return [expanderColumn, contestantColumn, questionColumn, scoreColumn, passFailColumn];
      case 'agent':
        return [scoreColumn, passFailColumn, breakdownColumn, reasoningColumn];
      default:
        return [scoreColumn, passFailColumn, breakdownColumn, reasoningColumn];
    }
  }, [evaluationMode, questionColumn]);

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
      <Link
        to="/results"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Results
      </Link>

      {/* Summary Header */}
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

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <ScoreDistributionChart results={results} />
        <PassFailChart passedItems={metrics.passed_items} failedItems={metrics.failed_items} />
      </div>

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
    </div>
  );
}
