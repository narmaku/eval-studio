import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';

import { useDatasetStore } from '@/stores/datasetStore';

interface DatasetDetailViewProps {
  datasetId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DatasetDetailView({ datasetId, open, onOpenChange }: DatasetDetailViewProps) {
  const { currentDataset, isLoading, fetchDataset, setCurrentDataset } = useDatasetStore();

  useEffect(() => {
    if (open && datasetId) {
      fetchDataset(datasetId);
    }
  }, [open, datasetId, fetchDataset]);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setCurrentDataset(null);
    }
    onOpenChange(nextOpen);
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-12" data-testid="detail-loading">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : currentDataset ? (
          <>
            <SheetHeader>
              <SheetTitle>{currentDataset.name}</SheetTitle>
              {currentDataset.description && (
                <SheetDescription>{currentDataset.description}</SheetDescription>
              )}
            </SheetHeader>

            <div className="grid grid-cols-2 gap-3 px-4">
              <div>
                <p className="text-xs text-muted-foreground">Format</p>
                <Badge variant="secondary">{currentDataset.format}</Badge>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Version</p>
                <p className="text-sm">{currentDataset.version}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Items</p>
                <p className="text-sm">{currentDataset.item_count}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Created</p>
                <p className="text-sm">
                  {new Date(currentDataset.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="col-span-2">
                <p className="text-xs text-muted-foreground">Tags</p>
                {currentDataset.tags.length > 0 ? (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {currentDataset.tags.map((tag) => (
                      <Badge key={tag} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No tags</p>
                )}
              </div>
            </div>

            <div className="px-4">
              <Separator />
            </div>

            <div className="px-4 space-y-3">
              <h3 className="text-sm font-medium">
                Items ({currentDataset.items?.length ?? 0})
              </h3>

              {currentDataset.items && currentDataset.items.length > 0 ? (
                <div className="max-h-[60vh] overflow-y-auto space-y-3">
                  {currentDataset.items.map((item, idx) => (
                    <div key={item.id} className="rounded-md border p-3 space-y-1">
                      <p className="text-xs text-muted-foreground">#{idx + 1}</p>
                      <p className="text-sm font-medium">{item.question}</p>
                      {item.expected_answer && (
                        <p className="text-sm text-muted-foreground">{item.expected_answer}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Load full dataset to view items
                </p>
              )}
            </div>
          </>
        ) : (
          <div className="flex justify-center py-12">
            <p className="text-sm text-muted-foreground">No dataset selected</p>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
