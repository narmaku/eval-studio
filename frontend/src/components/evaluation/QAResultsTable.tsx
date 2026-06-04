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
import type { Result, DatasetItem } from '@/types';

interface QAResultsTableProps {
  results: Result[];
  datasetItems?: DatasetItem[];
  onRowClick?: (result: Result) => void;
}

function truncate(text: string | null | undefined, maxLength: number): string {
  if (!text) return '--';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

export function QAResultsTable({ results, datasetItems, onRowClick }: QAResultsTableProps) {
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
          <span className="block max-w-[200px] truncate" title={getValue<string>()}>
            {truncate(getValue<string>(), 80)}
          </span>
        ),
      },
      {
        id: 'expected',
        header: 'Expected Answer',
        accessorFn: (row) => {
          const item = row.dataset_item_id ? itemMap.get(row.dataset_item_id) : undefined;
          return item?.expected_answer ?? '';
        },
        cell: ({ getValue }) => (
          <span className="block max-w-[200px] truncate" title={getValue<string>()}>
            {truncate(getValue<string>(), 60)}
          </span>
        ),
      },
      {
        id: 'actual',
        header: 'Actual Answer',
        accessorFn: (row) => row.actual_answer,
        cell: ({ getValue }) => (
          <span className="block max-w-[200px] truncate" title={getValue<string>() ?? ''}>
            {truncate(getValue<string>(), 60)}
          </span>
        ),
      },
      {
        id: 'score',
        header: ({ column }) => (
          <button
            type="button"
            className="flex items-center gap-1"
            onClick={() => column.toggleSorting()}
          >
            Score
            <ArrowUpDownIcon className="size-3" />
          </button>
        ),
        accessorFn: (row) => row.score ?? 0,
        cell: ({ getValue }) => (
          <span className="text-right tabular-nums">{(getValue<number>() * 100).toFixed(0)}%</span>
        ),
        enableSorting: true,
      },
      {
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
                    <ExpandedRowDetail
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

function ExpandedRowDetail({ result, datasetItem }: { result: Result; datasetItem?: DatasetItem }) {
  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="font-medium">Question</p>
        <p className="text-muted-foreground">
          {datasetItem?.question ?? result.dataset_item_id ?? '--'}
        </p>
      </div>
      <div>
        <p className="font-medium">Expected Answer</p>
        <p className="text-muted-foreground whitespace-pre-line">{datasetItem?.expected_answer ?? 'N/A'}</p>
      </div>
      <div>
        <p className="font-medium">Actual Answer</p>
        <p className="text-muted-foreground whitespace-pre-line">{result.actual_answer || 'N/A'}</p>
      </div>
      <div>
        <p className="font-medium">Judge Reasoning</p>
        <blockquote className="mt-1 border-l-2 border-muted-foreground/30 pl-3 text-muted-foreground italic whitespace-pre-line">
          {result.judge_reasoning || 'No reasoning provided.'}
        </blockquote>
      </div>
    </div>
  );
}
