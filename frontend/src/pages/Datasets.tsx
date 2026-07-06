import { useEffect, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Database,
  Loader2,
  Pencil,
  Star,
  Trash2,
  Upload,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { formatMonoDate } from '@/lib/designUtils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { useDatasetStore } from '@/stores/datasetStore';
import { SmartImportDialog } from '@/components/datasets/SmartImportDialog';
import { DatasetDetailView } from '@/components/datasets/DatasetDetailView';
import { DatasetEditSheet } from '@/components/datasets/DatasetEditSheet';
import type { Dataset } from '@/types';

const columns: ColumnDef<Dataset>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => (
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
      >
        Name
        {column.getIsSorted() === 'asc' ? (
          <ArrowUp className="ml-1 h-4 w-4" />
        ) : column.getIsSorted() === 'desc' ? (
          <ArrowDown className="ml-1 h-4 w-4" />
        ) : (
          <ArrowUpDown className="ml-1 h-4 w-4" />
        )}
      </Button>
    ),
    cell: ({ row }) => (
      <span className="font-medium cursor-pointer hover:underline">{row.getValue('name')}</span>
    ),
  },
  {
    accessorKey: 'format',
    header: ({ column }) => (
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
      >
        Format
        {column.getIsSorted() === 'asc' ? (
          <ArrowUp className="ml-1 h-4 w-4" />
        ) : column.getIsSorted() === 'desc' ? (
          <ArrowDown className="ml-1 h-4 w-4" />
        ) : (
          <ArrowUpDown className="ml-1 h-4 w-4" />
        )}
      </Button>
    ),
    cell: ({ row }) => <Badge variant="secondary">{row.getValue('format')}</Badge>,
  },
  {
    accessorKey: 'item_count',
    header: ({ column }) => (
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
      >
        Items
        {column.getIsSorted() === 'asc' ? (
          <ArrowUp className="ml-1 h-4 w-4" />
        ) : column.getIsSorted() === 'desc' ? (
          <ArrowDown className="ml-1 h-4 w-4" />
        ) : (
          <ArrowUpDown className="ml-1 h-4 w-4" />
        )}
      </Button>
    ),
    cell: ({ row }) => <span className="text-right">{row.getValue('item_count')}</span>,
  },
  {
    accessorKey: 'created_at',
    header: ({ column }) => (
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
      >
        Created
        {column.getIsSorted() === 'asc' ? (
          <ArrowUp className="ml-1 h-4 w-4" />
        ) : column.getIsSorted() === 'desc' ? (
          <ArrowDown className="ml-1 h-4 w-4" />
        ) : (
          <ArrowUpDown className="ml-1 h-4 w-4" />
        )}
      </Button>
    ),
    cell: ({ row }) => (
      <span className="font-mono text-[11px] text-text-2">
        {formatMonoDate(row.getValue('created_at') as string)}
      </span>
    ),
  },
];

export default function Datasets() {
  const { datasets, isLoading, error, fetchDatasets, removeDataset } = useDatasetStore();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Dataset | null>(null);
  const [editTarget, setEditTarget] = useState<Dataset | null>(null);
  const [detailTarget, setDetailTarget] = useState<Dataset | null>(null);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error]);

  const table = useReactTable({
    data: datasets,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await removeDataset(deleteTarget.id);
      toast.success(`Dataset "${deleteTarget.name}" deleted`);
    } catch {
      // error is already set in the store
    }
    setDeleteTarget(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[25px] font-semibold tracking-[-0.02em]">Datasets</h1>
          <p className="text-[13px] text-text-2">
            Your dataset library. Upload, import, version, and browse evaluation datasets.
          </p>
        </div>
        <button
          className="flex items-center gap-2 rounded-[9px] bg-primary px-4 py-2.5 text-[13px] font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
          onClick={() => setUploadDialogOpen(true)}
        >
          <Upload className="h-4 w-4" />
          Import Dataset
        </button>
      </div>

      {/* Smart-import banner */}
      <div className="rounded-[14px] border border-dashed border-border bg-accent/10 p-5">
        <div className="flex items-center gap-3">
          <Star className="h-5 w-5 shrink-0 text-primary" />
          <div>
            <p className="text-[13px] font-medium">Smart import auto-detects your format</p>
            <p className="text-[12px] text-text-2">
              Drop any CSV, JSON, JSONL, or YAML file and we will parse it automatically.
            </p>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12" data-testid="datasets-loading">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : datasets.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mb-4" />
            <h2 className="text-lg font-semibold">No datasets yet</h2>
            <p className="text-sm text-muted-foreground mt-1 mb-4">
              Upload a dataset to get started with your evaluations.
            </p>
            <Button onClick={() => setUploadDialogOpen(true)}>Import Dataset</Button>
          </CardContent>
        </Card>
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
                  <TableHead>Actions</TableHead>
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell
                      key={cell.id}
                      onClick={() => {
                        if (cell.column.id === 'name') {
                          setDetailTarget(row.original);
                        }
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                  <TableCell>
                    <div className="flex gap-1">
                      <button
                        className="rounded-[9px] p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                        onClick={() => setEditTarget(row.original)}
                        aria-label={`Edit ${row.original.name}`}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        className="rounded-[9px] p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                        onClick={() => setDeleteTarget(row.original)}
                        aria-label={`Delete ${row.original.name}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete dataset</DialogTitle>
            <DialogDescription>
              Delete dataset &quot;{deleteTarget?.name}&quot;? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Sheet */}
      {editTarget && (
        <DatasetEditSheet
          open={!!editTarget}
          onOpenChange={(open) => !open && setEditTarget(null)}
          dataset={editTarget}
        />
      )}

      {/* Import Dialog */}
      <SmartImportDialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen} />

      {/* Detail Sheet */}
      <DatasetDetailView
        datasetId={detailTarget?.id ?? null}
        open={!!detailTarget}
        onOpenChange={(open) => !open && setDetailTarget(null)}
      />
    </div>
  );
}
