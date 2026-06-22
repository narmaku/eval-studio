import { useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useHarnessStore } from '@/stores/harnessStore';

interface HarnessSelectorProps {
  value?: string;
  onChange: (harnessId: string, harnessType: string) => void;
  disabled?: boolean;
}

export function HarnessSelector({ value, onChange, disabled }: HarnessSelectorProps) {
  const { harnesses, isLoading, fetchHarnesses } = useHarnessStore();

  useEffect(() => {
    void fetchHarnesses();
  }, [fetchHarnesses]);

  // Find the default harness for initial selection
  useEffect(() => {
    if (!value && harnesses.length > 0) {
      const defaultHarness = harnesses.find((h) => h.default && h.enabled);
      if (defaultHarness) {
        onChange(defaultHarness.id, defaultHarness.type);
      }
    }
  }, [harnesses, value, onChange]);

  const handleSelect = (harnessId: string) => {
    const harness = harnesses.find((h) => h.id === harnessId);
    if (harness) {
      onChange(harness.id, harness.type);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Agent Harness</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Loading harnesses...</p>
        </CardContent>
      </Card>
    );
  }

  // Don't render if there's only the builtin harness
  if (harnesses.length <= 1) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Agent Harness</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Select value={value} onValueChange={handleSelect} disabled={disabled}>
          <SelectTrigger className="w-full" data-testid="harness-select">
            <SelectValue placeholder="Select a harness..." />
          </SelectTrigger>
          <SelectContent>
            {harnesses.map((harness) => (
              <SelectItem key={harness.id} value={harness.id} disabled={!harness.enabled}>
                <span className="flex items-center gap-2">
                  <span
                    className={`font-medium ${!harness.enabled ? 'text-muted-foreground' : ''}`}
                  >
                    {harness.name}
                  </span>
                  <Badge
                    variant={harness.type === 'builtin' ? 'secondary' : 'outline'}
                    className="text-[10px] px-1 py-0"
                  >
                    {harness.type}
                  </Badge>
                  {!harness.enabled && (
                    <span className="text-muted-foreground text-xs">(Disabled)</span>
                  )}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {value && harnesses.find((h) => h.id === value)?.description && (
          <p className="text-xs text-muted-foreground">
            {harnesses.find((h) => h.id === value)?.description}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
