import { useEffect, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown, Database, Loader2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
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
    cell: ({ row }) => new Date(row.getValue('created_at') as string).toLocaleDateString(),
  },
];

export default function Datasets() {
  const { datasets, isLoading, error, fetchDatasets, removeDataset } = useDatasetStore();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Dataset | null>(null);
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
          <h1 className="text-3xl font-bold tracking-tight">Datasets</h1>
          <p className="text-muted-foreground">
            Manage your dataset library. Upload, import, version, and browse evaluation datasets.
          </p>
        </div>
        <Button onClick={() => setUploadDialogOpen(true)}>Import Dataset</Button>
      </div>

      <Separator />

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
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setDeleteTarget(row.original)}
                      aria-label={`Delete ${row.original.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
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
