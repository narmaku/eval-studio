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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { ChevronDownIcon, ChevronRightIcon, ArrowUpDownIcon } from 'lucide-react';
import { ChunkDisplay } from './ChunkDisplay';
import type { Result, DatasetItem } from '@/types';

interface RAGResultsTableProps {
  results: Result[];
  datasetItems?: DatasetItem[];
  onRowClick?: (result: Result) => void;
}

function truncate(text: string | null | undefined, maxLength: number): string {
  if (!text) return '--';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

function metricCell(result: Result, metric: string): string {
  const value = result.scores_breakdown?.[metric];
  if (value === undefined || value === null) return '--';
  return `${(value * 100).toFixed(0)}%`;
}

export function RAGResultsTable({ results, datasetItems, onRowClick }: RAGResultsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [expanded, setExpanded] = useState<ExpandedState>({});

  const itemMap = useMemo(() => {
    const map = new Map<string, DatasetItem>();
    datasetItems?.forEach((item) => map.set(item.id, item));
    return map;
  }, [datasetItems]);

  const columns = useMemo<ColumnDef<Result>[]>(
    () => [
      {
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
              <ChevronDownIcon className="size-4" />
            ) : (
              <ChevronRightIcon className="size-4" />
            )}
          </button>
        ),
        size: 32,
      },
      {
        id: 'question',
        header: 'Question',
        accessorFn: (row) => {
          const item = row.dataset_item_id ? itemMap.get(row.dataset_item_id) : undefined;
          return item?.question ?? row.dataset_item_id ?? '--';
        },
        cell: ({ getValue }) => (
          <span className="block max-w-[180px] truncate" title={getValue<string>()}>
            {truncate(getValue<string>(), 60)}
          </span>
        ),
      },
      {
        id: 'expected',
        header: 'Expected',
        accessorFn: (row) => {
          const item = row.dataset_item_id ? itemMap.get(row.dataset_item_id) : undefined;
          return item?.expected_answer ?? '';
        },
        cell: ({ getValue }) => (
          <span className="block max-w-[150px] truncate" title={getValue<string>()}>
            {truncate(getValue<string>(), 40)}
          </span>
        ),
      },
      {
        id: 'actual',
        header: 'Actual Answer',
        accessorFn: (row) => row.actual_answer,
        cell: ({ getValue }) => (
          <span className="block max-w-[150px] truncate" title={getValue<string>() ?? ''}>
            {truncate(getValue<string>(), 40)}
          </span>
        ),
      },
      {
        id: 'chunks',
        header: 'Chunks',
        accessorFn: (row) => row.retrieved_chunks?.length ?? 0,
        cell: ({ getValue }) => {
          const count = getValue<number>();
          return (
            <Badge variant="secondary" className="tabular-nums">
              {count}
            </Badge>
          );
        },
      },
      {
        id: 'faithfulness',
        header: 'Faithfulness',
        accessorFn: (row) => row.scores_breakdown?.faithfulness ?? null,
        cell: ({ row }) => (
          <span className="tabular-nums">{metricCell(row.original, 'faithfulness')}</span>
        ),
      },
      {
        id: 'precision',
        header: 'Precision',
        accessorFn: (row) => row.scores_breakdown?.context_precision ?? null,
        cell: ({ row }) => (
          <span className="tabular-nums">{metricCell(row.original, 'context_precision')}</span>
        ),
      },
      {
        id: 'relevance',
        header: ({ column }) => (
          <button
            type="button"
            className="flex items-center gap-1"
            onClick={() => column.toggleSorting()}
          >
            Relevance
            <ArrowUpDownIcon className="size-3" />
          </button>
        ),
        accessorFn: (row) => row.scores_breakdown?.answer_relevance ?? null,
        cell: ({ row }) => (
          <span className="tabular-nums">{metricCell(row.original, 'answer_relevance')}</span>
        ),
        enableSorting: true,
      },
    ],
    [itemMap],
  );

  const table = useReactTable({
    data: results,
    columns,
    state: { sorting, expanded },
    onSortingChange: setSorting,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: () => true,
  });

  return (
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
            <TableCell colSpan={columns.length} className="text-center text-muted-foreground">
              No results to display.
            </TableCell>
          </TableRow>
        ) : (
          table.getRowModel().rows.map((row) => (
            <Fragment key={row.id}>
              <TableRow className="cursor-pointer" onClick={() => onRowClick?.(row.original)}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
              {row.getIsExpanded() && (
                <TableRow>
                  <TableCell colSpan={columns.length} className="bg-muted/30 p-4">
                    <RAGExpandedRowDetail
                      result={row.original}
                      datasetItem={
                        row.original.dataset_item_id
                          ? itemMap.get(row.original.dataset_item_id)
                          : undefined
                      }
                    />
                  </TableCell>
                </TableRow>
              )}
            </Fragment>
          ))
        )}
      </TableBody>
    </Table>
  );
}

function RAGExpandedRowDetail({
  result,
  datasetItem,
}: {
  result: Result;
  datasetItem?: DatasetItem;
}) {
  const breakdown = result.scores_breakdown ?? {};
  const hasBreakdown = Object.keys(breakdown).length > 0;

  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="font-medium">Question</p>
        <p className="text-muted-foreground">
          {datasetItem?.question ?? result.dataset_item_id ?? '--'}
        </p>
      </div>
      <div>
        <p className="font-medium">Actual Answer</p>
        <p className="text-muted-foreground whitespace-pre-line">{result.actual_answer || 'N/A'}</p>
      </div>
      {result.retrieved_chunks && result.retrieved_chunks.length > 0 && (
        <div>
          <p className="font-medium mb-2">Retrieved Chunks</p>
          <ChunkDisplay chunks={result.retrieved_chunks} />
        </div>
      )}
      {hasBreakdown && (
        <div>
          <p className="font-medium">Metric Breakdown</p>
          <ul className="mt-1 space-y-1">
            {Object.entries(breakdown).map(([name, value]) => (
              <li key={name} className="flex justify-between">
                <span className="text-muted-foreground">{name}</span>
                <span className="tabular-nums">{(value * 100).toFixed(0)}%</span>
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
