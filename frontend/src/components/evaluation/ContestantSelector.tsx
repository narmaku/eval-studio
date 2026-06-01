import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProviderSelector } from '@/components/evaluation/ProviderSelector';
import type { ModelEndpoint } from '@/types';

const MIN_CONTESTANTS = 2;
const MAX_CONTESTANTS = 8;

interface ContestantSelectorProps {
  value: ModelEndpoint[];
  onChange: (contestants: ModelEndpoint[]) => void;
  disabled?: boolean;
}

export function ContestantSelector({ value, onChange, disabled }: ContestantSelectorProps) {
  // Internal slot count tracks how many contestant cards to show.
  // When value is empty, we start with MIN_CONTESTANTS empty slots.
  const [slotCount, setSlotCount] = useState(Math.max(value.length, MIN_CONTESTANTS));

  const effectiveSlotCount = Math.max(slotCount, value.length, MIN_CONTESTANTS);
  const canAdd = effectiveSlotCount < MAX_CONTESTANTS && !disabled;
  const canRemove = effectiveSlotCount > MIN_CONTESTANTS && !disabled;

  const handleAdd = () => {
    if (effectiveSlotCount < MAX_CONTESTANTS) {
      setSlotCount(effectiveSlotCount + 1);
    }
  };

  const handleRemove = (index: number) => {
    if (effectiveSlotCount <= MIN_CONTESTANTS) return;

    const newContestants = [...value];
    if (index < newContestants.length) {
      newContestants.splice(index, 1);
      onChange(newContestants);
    }
    setSlotCount(Math.max(effectiveSlotCount - 1, MIN_CONTESTANTS));
  };

  const handleContestantChange = (index: number, endpoint: ModelEndpoint) => {
    const newContestants = [...value];
    // Pad array with empty slots if needed
    while (newContestants.length <= index) {
      newContestants.push({ name: '', litellm_model: '' });
    }
    newContestants[index] = endpoint;
    onChange(newContestants);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Contestants</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {Array.from({ length: effectiveSlotCount }, (_, index) => {
          const contestant = index < value.length ? value[index] : undefined;
          return (
            <div key={index} className="relative rounded-lg border p-3">
              <div className="mb-2 flex items-center justify-between">
                <Badge variant="secondary">#{index + 1}</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={!canRemove}
                  onClick={() => handleRemove(index)}
                  aria-label={`Remove contestant ${index + 1}`}
                >
                  Remove
                </Button>
              </div>
              <ProviderSelector
                value={contestant}
                onChange={(endpoint) => handleContestantChange(index, endpoint)}
                disabled={disabled}
              />
            </div>
          );
        })}

        <Button variant="outline" className="w-full" disabled={!canAdd} onClick={handleAdd}>
          Add Contestant
        </Button>
      </CardContent>
    </Card>
  );
}
