import { useMemo, useState, useCallback } from 'react';
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
import { ArrowUpDown, Pencil, RotateCcw, Star, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { EvaluationEditSheet } from '@/components/evaluation/EvaluationEditSheet';
import { DeleteConfirmDialog } from '@/components/ui/delete-confirm-dialog';
import { RerunDialog } from '@/components/results/RerunDialog';
import { useResultStore } from '@/stores/resultStore';
import { useEvaluationStore } from '@/stores/evaluationStore';
import {
  getModeBadgeClasses,
  getModeLabel,
  getStatusPillClasses,
  getScoreColorClass,
  formatMonoDate,
} from '@/lib/designUtils';
import { cn } from '@/lib/utils';
import { extractConfigMetadata, mergeMetadata, filterSensitiveKeys } from '@/lib/metadataUtils';
import { MetadataBadges } from '@/components/ui/MetadataBadges';
import type { Evaluation, EvaluationConfig, EvaluationMode, EvaluationStatus } from '@/types';

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
  datasetId: string | null;
  config?: EvaluationConfig;
  metadata?: Record<string, string> | null;
}

/**
 * Check if a row is compatible with the current selection filter.
 * Compatible means same mode and same datasetId as the first selected evaluation.
 */
function isRowCompatible(
  row: EvaluationResultRow,
  filterMode: EvaluationMode | null,
  filterDatasetId: string | null,
): boolean {
  if (filterMode === null) return true; // No selection active
  return row.mode === filterMode && row.datasetId === filterDatasetId;
}

/**
 * Build a tooltip explaining why a row is incompatible.
 */
function incompatibilityReason(
  row: EvaluationResultRow,
  filterMode: EvaluationMode | null,
  filterDatasetId: string | null,
): string {
  const reasons: string[] = [];
  if (filterMode !== null && row.mode !== filterMode) {
    reasons.push(`Different mode (${row.mode} vs ${filterMode})`);
  }
  if (filterMode !== null && row.datasetId !== filterDatasetId) {
    reasons.push('Different dataset');
  }
  return reasons.join('; ');
}

interface EvaluationResultsListProps {
  rows: EvaluationResultRow[];
}

export function EvaluationResultsList({ rows }: EvaluationResultsListProps) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<SortingState>([{ id: 'createdAt', desc: true }]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [editTarget, setEditTarget] = useState<Evaluation | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<EvaluationResultRow | null>(null);
  const [rerunTarget, setRerunTarget] = useState<EvaluationResultRow | null>(null);

  const { evaluations, deleteEvaluation, fetchEvaluations } = useEvaluationStore();

  const selectedEvaluationIds = useResultStore((s) => s.selectedEvaluationIds);
  const referenceEvaluationId = useResultStore((s) => s.referenceEvaluationId);
  const toggleSelection = useResultStore((s) => s.toggleSelection);
  const setReference = useResultStore((s) => s.setReference);

  // Compute the compatibility filter based on the first selected evaluation
  const { filterMode, filterDatasetId } = useMemo(() => {
    if (selectedEvaluationIds.length === 0) {
      return { filterMode: null, filterDatasetId: null };
    }
    const firstSelectedId = selectedEvaluationIds[0];
    const firstSelected = rows.find((r) => r.evaluationId === firstSelectedId);
    if (!firstSelected) {
      return { filterMode: null, filterDatasetId: null };
    }
    return {
      filterMode: firstSelected.mode,
      filterDatasetId: firstSelected.datasetId,
    };
  }, [selectedEvaluationIds, rows]);

  const handleCheckboxClick = useCallback(
    (evaluationId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      toggleSelection(evaluationId);
    },
    [toggleSelection],
  );

  const handleSetReference = useCallback(
    (evaluationId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setReference(evaluationId);
    },
    [setReference],
  );

  const columns = useMemo<ColumnDef<EvaluationResultRow>[]>(
    () => [
      {
        id: 'select',
        header: () => null,
        cell: ({ row }) => {
          const evalId = row.original.evaluationId;
          const isSelected = selectedEvaluationIds.includes(evalId);
          const isReference = referenceEvaluationId === evalId;
          const compatible = isRowCompatible(row.original, filterMode, filterDatasetId);
          const isDisabled = !compatible && !isSelected;
          const tooltip = isDisabled
            ? incompatibilityReason(row.original, filterMode, filterDatasetId)
            : undefined;

          return (
            <div className="flex items-center gap-1">
              <div title={tooltip}>
                <Checkbox
                  checked={isSelected}
                  disabled={isDisabled}
                  onClick={(e) => handleCheckboxClick(evalId, e)}
                  onCheckedChange={() => {
                    /* handled by onClick to stop propagation */
                  }}
                  aria-label={`Select ${row.original.name}`}
                />
              </div>
              {isSelected && (
                <button
                  title={isReference ? 'Reference evaluation' : 'Set as reference'}
                  onClick={(e) => handleSetReference(evalId, e)}
                  className="p-0.5"
                >
                  <Star
                    className={`h-4 w-4 ${isReference ? 'fill-yellow-400 text-yellow-500' : 'text-muted-foreground'}`}
                  />
                </button>
              )}
            </div>
          );
        },
        enableSorting: false,
      },
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
        cell: ({ row }) => {
          const configMeta = row.original.config
            ? filterSensitiveKeys(extractConfigMetadata(row.original.config))
            : {};
          const merged = mergeMetadata(configMeta, row.original.metadata);
          return (
            <div className="space-y-1">
              <span className="font-medium" title={row.original.name}>
                {row.original.name}
              </span>
              {row.original.metadata?.is_rerun === 'true' && (
                <span className="text-[10px] text-muted-foreground">
                  Re-run of: {row.original.metadata?.original_run_name}
                </span>
              )}
              <MetadataBadges metadata={merged} maxInline={3} compact />
            </div>
          );
        },
      },
      {
        accessorKey: 'mode',
        header: 'Mode',
        cell: ({ row }) => (
          <span
            className={cn(
              'rounded-[6px] px-2 py-0.5 text-[10px] font-semibold uppercase',
              getModeBadgeClasses(row.original.mode),
            )}
          >
            {getModeLabel(row.original.mode)}
          </span>
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
          <span
            className={cn(
              'rounded-full px-2.5 py-0.5 text-[10.5px] font-medium capitalize',
              getStatusPillClasses(row.original.status),
            )}
          >
            {row.original.status}
          </span>
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
        cell: ({ row }) => (
          <span className="font-mono tabular-nums">
            {row.original.status === 'failed'
              ? '—'
              : `${(row.original.passRate * 100).toFixed(1)}%`}
          </span>
        ),
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
        cell: ({ row }) => (
          <span
            className={cn(
              'font-mono font-semibold tabular-nums',
              row.original.status === 'failed'
                ? 'text-text-3'
                : getScoreColorClass(row.original.meanScore),
            )}
          >
            {row.original.status === 'failed' ? '—' : row.original.meanScore.toFixed(3)}
          </span>
        ),
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
        cell: ({ row }) => (
          <span className="font-mono text-[11px] text-text-2">
            {formatMonoDate(row.original.createdAt)}
          </span>
        ),
        sortingFn: (rowA, rowB) => {
          return (
            new Date(rowA.original.createdAt).getTime() -
            new Date(rowB.original.createdAt).getTime()
          );
        },
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Re-run evaluation"
              onClick={(e) => {
                e.stopPropagation();
                setRerunTarget(row.original);
              }}
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Edit evaluation"
              onClick={(e) => {
                e.stopPropagation();
                const eval_ = evaluations.find((ev) => ev.id === row.original.evaluationId);
                if (eval_) setEditTarget(eval_);
              }}
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Delete evaluation"
              onClick={(e) => {
                e.stopPropagation();
                setDeleteTarget(row.original);
              }}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ),
        enableSorting: false,
      },
    ],
    [
      selectedEvaluationIds,
      referenceEvaluationId,
      filterMode,
      filterDatasetId,
      handleCheckboxClick,
      handleSetReference,
      evaluations,
    ],
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
            {table.getRowModel().rows.map((row) => {
              const evalId = row.original.evaluationId;
              const isSelected = selectedEvaluationIds.includes(evalId);
              const compatible = isRowCompatible(row.original, filterMode, filterDatasetId);
              const isIncompatible = !compatible && !isSelected;
              const isReference = referenceEvaluationId === evalId;
              const tooltip = isIncompatible
                ? incompatibilityReason(row.original, filterMode, filterDatasetId)
                : undefined;

              return (
                <TableRow
                  key={row.id}
                  className={`cursor-pointer ${isIncompatible ? 'opacity-40' : ''} ${isReference ? 'bg-yellow-50 dark:bg-yellow-950/20' : ''}`}
                  title={tooltip}
                  onClick={() => navigate(`/results/${row.original.resultId}`)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {editTarget && (
        <EvaluationEditSheet
          open={!!editTarget}
          onOpenChange={(open) => {
            if (!open) {
              setEditTarget(null);
              void fetchEvaluations();
            }
          }}
          evaluation={editTarget}
        />
      )}

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Delete evaluation"
        description="Are you sure you want to delete this evaluation?"
        entityName={deleteTarget?.name ?? ''}
        onConfirm={async () => {
          if (!deleteTarget) return;
          await deleteEvaluation(deleteTarget.evaluationId);
          toast.success(`Evaluation "${deleteTarget.name}" deleted`);
          setDeleteTarget(null);
        }}
        cascadeInfo="All results and artifacts for this evaluation will also be deleted."
      />

      {rerunTarget && (
        <RerunDialog
          open={!!rerunTarget}
          onOpenChange={(open) => {
            if (!open) setRerunTarget(null);
          }}
          evaluation={rerunTarget}
          onSuccess={() => {
            setRerunTarget(null);
            void fetchEvaluations();
          }}
        />
      )}
    </div>
  );
}
