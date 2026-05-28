import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
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
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { useRubricStore } from '@/stores/rubricStore';
import { RubricBuilder } from './RubricBuilder';
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
    if (deleteTarget) {
      await deleteRubric(deleteTarget.id);
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
          className="max-w-sm"
        />
        <Button onClick={handleNew}>
          <Plus className="mr-1 h-4 w-4" />
          New Rubric
        </Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <p className="text-sm text-muted-foreground">Loading rubrics...</p>
        </div>
      )}

      {!isLoading && filteredRubrics.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12">
          <p className="text-sm text-muted-foreground">
            No rubrics created yet. Create your first rubric to define custom scoring criteria.
          </p>
        </div>
      )}

      {filteredRubrics.map((rubric) => (
        <Card key={rubric.id}>
          <CardContent className="flex items-center justify-between py-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="font-medium">{rubric.name}</h3>
                <Badge variant="secondary">
                  {rubric.dimensions.length}{' '}
                  {rubric.dimensions.length === 1 ? 'dimension' : 'dimensions'}
                </Badge>
                <Badge variant="outline">{rubric.aggregation}</Badge>
              </div>
              {rubric.description && (
                <p className="text-xs text-muted-foreground line-clamp-1">
                  {rubric.description}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Threshold: {rubric.pass_threshold} | Created:{' '}
                {new Date(rubric.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" onClick={() => handleEdit(rubric)} aria-label="Edit">
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDeleteTarget(rubric)}
                aria-label="Delete"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}

      <RubricBuilder
        open={builderOpen}
        onOpenChange={setBuilderOpen}
        rubric={editingRubric}
        onSaved={handleSaved}
      />

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
