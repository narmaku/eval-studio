import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';

interface RAGMetricsSelectorProps {
  value: string[];
  onChange: (metrics: string[]) => void;
  disabled?: boolean;
}

interface MetricOption {
  id: string;
  label: string;
  description: string;
}

const RAG_METRICS: MetricOption[] = [
  {
    id: 'context_precision',
    label: 'Context Precision',
    description: 'Are retrieved chunks relevant?',
  },
  {
    id: 'context_recall',
    label: 'Context Recall',
    description: 'Do chunks cover needed info?',
  },
  {
    id: 'faithfulness',
    label: 'Faithfulness',
    description: 'Is answer grounded in chunks?',
  },
  {
    id: 'answer_relevance',
    label: 'Answer Relevance',
    description: 'Does answer address the question?',
  },
];

// eslint-disable-next-line react-refresh/only-export-components
export const ALL_RAG_METRICS = RAG_METRICS.map((m) => m.id);

export function RAGMetricsSelector({ value, onChange, disabled }: RAGMetricsSelectorProps) {
  const handleToggle = (metricId: string) => {
    if (value.includes(metricId)) {
      onChange(value.filter((id) => id !== metricId));
    } else {
      onChange([...value, metricId]);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">RAG Metrics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {RAG_METRICS.map((metric) => {
          const checked = value.includes(metric.id);
          return (
            <div key={metric.id} className="flex items-start gap-3">
              <input
                type="checkbox"
                id={`metric-${metric.id}`}
                checked={checked}
                onChange={() => handleToggle(metric.id)}
                disabled={disabled}
                className="mt-0.5 size-4 rounded border-input accent-primary"
              />
              <Label htmlFor={`metric-${metric.id}`} className="cursor-pointer">
                <span className="text-sm font-medium">{metric.label}</span>
                <p className="text-xs text-muted-foreground">{metric.description}</p>
              </Label>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
