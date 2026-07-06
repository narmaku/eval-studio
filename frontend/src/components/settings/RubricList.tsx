import { useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Plus, Pencil, Trash2, Upload, Sparkles, RefreshCw } from 'lucide-react';
import { useRubricStore } from '@/stores/rubricStore';
import { RubricBuilder } from './RubricBuilder';
import { RubricImportDialog } from './RubricImportDialog';
import { RubricGenerateDialog } from './RubricGenerateDialog';
import { RubricRefineDialog } from './RubricRefineDialog';
import { formatMonoDate } from '@/lib/designUtils';
import type { Rubric } from '@/types';

export function RubricList() {
  const rubrics = useRubricStore((s) => s.rubrics);
  const isLoading = useRubricStore((s) => s.isLoading);
  const fetchRubrics = useRubricStore((s) => s.fetchRubrics);
  const deleteRubric = useRubricStore((s) => s.deleteRubric);

  const [filter, setFilter] = useState('');
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingRubric, setEditingRubric] = useState<Rubric | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Rubric | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [refineTarget, setRefineTarget] = useState<Rubric | null>(null);

  useEffect(() => {
    fetchRubrics();
  }, [fetchRubrics]);

  const filteredRubrics = filter
    ? rubrics.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
    : rubrics;

  const handleEdit = (rubric: Rubric) => {
    setEditingRubric(rubric);
    setBuilderOpen(true);
  };

  const handleNew = () => {
    setEditingRubric(undefined);
    setBuilderOpen(true);
  };

  const handleSaved = () => {
    fetchRubrics();
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteRubric(deleteTarget.id);
    } catch {
      // deleteRubric propagates API errors; swallow here since store.error
      // is not set by deleteRubric -- surface feedback via a re-fetch so
      // the list stays consistent with the server state.
      await fetchRubrics();
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Filter rubrics..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-[260px]"
        />
        <div className="flex gap-2">
          <button
            className="inline-flex items-center rounded-[9px] border border-border px-3 py-1.5 text-[12px] font-medium text-text-2 transition-colors hover:bg-surface-3"
            onClick={() => setImportOpen(true)}
          >
            <Upload className="mr-1 h-3.5 w-3.5" />
            Import
          </button>
          <button
            className="inline-flex items-center rounded-[9px] border border-border px-3 py-1.5 text-[12px] font-medium text-text-2 transition-colors hover:bg-surface-3"
            onClick={() => setGenerateOpen(true)}
          >
            <Sparkles className="mr-1 h-3.5 w-3.5" />
            Generate
          </button>
          <button
            className="inline-flex items-center rounded-[9px] bg-primary px-4 py-2.5 text-[13px] font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
            onClick={handleNew}
          >
            <Plus className="mr-1 h-3.5 w-3.5" />
            New Rubric
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <p className="text-[13px] text-text-3">Loading rubrics...</p>
        </div>
      )}

      {!isLoading && filteredRubrics.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-[14px] border border-dashed border-border py-12">
          <p className="text-[13px] text-text-3">
            No rubrics created yet. Create your first rubric to define custom scoring criteria.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredRubrics.map((rubric) => (
          <div
            key={rubric.id}
            className="flex flex-col rounded-[14px] border border-border bg-card p-5 shadow-sm transition-all hover:shadow"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-[14px] font-semibold">{rubric.name}</h3>
              </div>
              <div className="flex items-center gap-0.5 shrink-0">
                <button
                  className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                  onClick={() => setRefineTarget(rubric)}
                  aria-label="Refine"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
                <button
                  className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                  onClick={() => handleEdit(rubric)}
                  aria-label="Edit"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  className="rounded-md p-1.5 text-text-3 transition-colors hover:bg-surface-3 hover:text-foreground"
                  onClick={() => setDeleteTarget(rubric)}
                  aria-label="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="mt-2 space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                  {rubric.dimensions.length}{' '}
                  {rubric.dimensions.length === 1 ? 'dimension' : 'dimensions'}
                </span>
                <span className="rounded-[5px] bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] text-text-3">
                  {rubric.aggregation}
                </span>
              </div>
              {rubric.description && (
                <p className="text-[12px] text-text-2 line-clamp-2">{rubric.description}</p>
              )}
              <p className="font-mono text-[11px] text-text-2">
                Threshold: {rubric.pass_threshold} | {formatMonoDate(rubric.created_at)}
              </p>
            </div>
          </div>
        ))}
      </div>

      <RubricBuilder
        open={builderOpen}
        onOpenChange={setBuilderOpen}
        rubric={editingRubric}
        onSaved={handleSaved}
      />

      <RubricImportDialog open={importOpen} onOpenChange={setImportOpen} onImported={handleSaved} />

      <RubricGenerateDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        onGenerated={handleSaved}
      />

      {refineTarget && (
        <RubricRefineDialog
          open={!!refineTarget}
          onOpenChange={(open) => !open && setRefineTarget(null)}
          rubric={refineTarget}
          onRefined={handleSaved}
        />
      )}

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Rubric</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deleteTarget?.name}&quot;? This action cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
