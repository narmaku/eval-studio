import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { LLMParams } from '@/types';

interface LLMParamsPanelProps {
  label?: string;
  value: LLMParams;
  onChange: (params: LLMParams) => void;
}

const PARAM_DEFS = [
  {
    key: 'max_tokens' as const,
    label: 'Max Tokens',
    placeholder: 'Default',
    min: 1,
    max: undefined,
    step: 1,
  },
  {
    key: 'temperature' as const,
    label: 'Temperature',
    placeholder: 'Default',
    min: 0,
    max: 2,
    step: 0.1,
  },
  {
    key: 'top_p' as const,
    label: 'Top P',
    placeholder: 'Default',
    min: 0,
    max: 1,
    step: 0.1,
  },
  {
    key: 'frequency_penalty' as const,
    label: 'Frequency Penalty',
    placeholder: 'Default',
    min: -2,
    max: 2,
    step: 0.1,
  },
  {
    key: 'presence_penalty' as const,
    label: 'Presence Penalty',
    placeholder: 'Default',
    min: -2,
    max: 2,
    step: 0.1,
  },
] as const;

export function LLMParamsPanel({
  label = 'Advanced Parameters',
  value,
  onChange,
}: LLMParamsPanelProps) {
  const [open, setOpen] = useState(false);

  const activeCount = Object.keys(value).length;

  const handleChange = (key: keyof LLMParams, raw: string) => {
    if (raw === '') {
      const next = { ...value };
      delete next[key];
      onChange(next);
    } else {
      const num = parseFloat(raw);
      if (!isNaN(num)) {
        onChange({ ...value, [key]: num });
      }
    }
  };

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted/50"
        >
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          {label}
          {activeCount > 0 && (
            <span className="ml-auto rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
              {activeCount} set
            </span>
          )}
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid gap-3 border-x border-b rounded-b-md px-3 py-3 md:grid-cols-2">
          {PARAM_DEFS.map((param) => (
            <div key={param.key} className="space-y-1">
              <Label htmlFor={`llm-param-${param.key}`} className="text-xs">
                {param.label}
              </Label>
              <Input
                id={`llm-param-${param.key}`}
                type="number"
                min={param.min}
                max={param.max}
                step={param.step}
                placeholder={param.placeholder}
                value={value[param.key] ?? ''}
                onChange={(e) => handleChange(param.key, e.target.value)}
                className="h-8 text-sm"
              />
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
