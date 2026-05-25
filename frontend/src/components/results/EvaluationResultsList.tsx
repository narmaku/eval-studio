import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import { useNavigate } from 'react-router-dom';
import { ArrowUpDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { EvaluationMode, EvaluationStatus } from '@/types';

export interface EvaluationResultRow {
  evaluationId: string;
  resultId: string;
  name: string;
  mode: EvaluationMode;
  status: EvaluationStatus;
  totalItems: number;
  passRate: number;
  meanScore: number;
  createdAt: string;
}

const modeBadgeStyles: Record<EvaluationMode, string> = {
  qa: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  agent: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  rag: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  arena: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
};

const modeLabels: Record<EvaluationMode, string> = {
  qa: 'Q&A',
  agent: 'Agent',
  rag: 'RAG',
  arena: 'Arena',
};

const statusBadgeVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  completed: 'default',
  failed: 'destructive',
  pending: 'secondary',
  running: 'secondary',
  cancelled: 'outline',
};

interface EvaluationResultsListProps {
  rows: EvaluationResultRow[];
}

export function EvaluationResultsList({ rows }: EvaluationResultsListProps) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<SortingState>([{ id: 'createdAt', desc: true }]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const columns = useMemo<ColumnDef<EvaluationResultRow>[]>(
    () => [
      {
        accessorKey: 'name',
        header: ({ column }) => (
          <button
            className="flex items-center gap-1"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Name
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ row }) => (
          <span className="font-medium" title={row.original.name}>
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: 'mode',
        header: 'Mode',
        cell: ({ row }) => (
          <Badge variant="outline" className={modeBadgeStyles[row.original.mode]}>
            {modeLabels[row.original.mode]}
          </Badge>
        ),
        filterFn: (row, _columnId, filterValue: string) => {
          if (filterValue === 'all') return true;
          return row.original.mode === filterValue;
        },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ row }) => (
          <Badge variant={statusBadgeVariants[row.original.status] ?? 'secondary'}>
            {row.original.status}
          </Badge>
        ),
      },
      {
        accessorKey: 'totalItems',
        header: ({ column }) => (
          <button
            className="flex items-center gap-1"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Items Scored
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ row }) => row.original.totalItems,
      },
      {
        accessorKey: 'passRate',
        header: ({ column }) => (
          <button
            className="flex items-center gap-1"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Pass Rate
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ row }) => `${(row.original.passRate * 100).toFixed(1)}%`,
      },
      {
        accessorKey: 'meanScore',
        header: ({ column }) => (
          <button
            className="flex items-center gap-1"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Mean Score
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ row }) => row.original.meanScore.toFixed(3),
      },
      {
        accessorKey: 'createdAt',
        header: ({ column }) => (
          <button
            className="flex items-center gap-1"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Date
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: ({ row }) => new Date(row.original.createdAt).toLocaleDateString(),
        sortingFn: (rowA, rowB) => {
          return (
            new Date(rowA.original.createdAt).getTime() -
            new Date(rowB.original.createdAt).getTime()
          );
        },
      },
    ],
    [],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (rows.length === 0) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">No evaluation results yet.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Select
          value={(table.getColumn('mode')?.getFilterValue() as string) ?? 'all'}
          onValueChange={(value) => table.getColumn('mode')?.setFilterValue(value)}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Filter by mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Modes</SelectItem>
            <SelectItem value="qa">Q&A</SelectItem>
            <SelectItem value="agent">Agent</SelectItem>
            <SelectItem value="rag">RAG</SelectItem>
            <SelectItem value="arena">Arena</SelectItem>
          </SelectContent>
        </Select>
      </div>

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
            {table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                className="cursor-pointer"
                onClick={() => navigate(`/results/${row.original.resultId}`)}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
