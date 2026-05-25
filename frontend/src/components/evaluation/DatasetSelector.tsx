import { useEffect } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDatasetStore } from '@/stores/datasetStore';

interface DatasetSelectorProps {
  value: string | undefined;
  onChange: (datasetId: string) => void;
  disabled?: boolean;
}

export function DatasetSelector({ value, onChange, disabled }: DatasetSelectorProps) {
  const { datasets, isLoading, fetchDatasets } = useDatasetStore();

  useEffect(() => {
    void fetchDatasets();
  }, [fetchDatasets]);

  const isDisabled = disabled || isLoading;

  return (
    <Select value={value} onValueChange={onChange} disabled={isDisabled}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder={isLoading ? 'Loading datasets...' : 'Select a dataset...'} />
      </SelectTrigger>
      <SelectContent>
        {datasets.length === 0 && !isLoading ? (
          <div className="px-2 py-1.5 text-sm text-muted-foreground">No datasets available</div>
        ) : (
          datasets.map((dataset) => (
            <SelectItem key={dataset.id} value={dataset.id}>
              {dataset.name} -- {dataset.item_count} items
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  );
}
