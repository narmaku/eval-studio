import { useMemo } from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const COLORS = [
  'hsl(210, 80%, 55%)', // blue
  'hsl(340, 75%, 55%)', // pink
  'hsl(150, 65%, 45%)', // green
  'hsl(45, 90%, 50%)', // gold
  'hsl(270, 60%, 55%)', // purple
  'hsl(15, 80%, 55%)', // orange
];

interface RadarSeries {
  name: string;
  data: Record<string, number>;
}

interface RadarComparisonChartProps {
  series: RadarSeries[];
  title?: string;
}

export function RadarComparisonChart({
  series,
  title = 'Metric Comparison',
}: RadarComparisonChartProps) {
  const { radarData, metrics } = useMemo(() => {
    // Collect all metric keys across all series
    const allKeys = new Set<string>();
    for (const s of series) {
      Object.keys(s.data).forEach((k) => allKeys.add(k));
    }
    const metrics = Array.from(allKeys).sort();

    // Build data array for recharts: [{metric: "faithfulness", series1: 0.8, series2: 0.7}, ...]
    const radarData = metrics.map((metric) => {
      const point: Record<string, string | number> = { metric };
      for (const s of series) {
        point[s.name] = s.data[metric] ?? 0;
      }
      return point;
    });

    return { radarData, metrics };
  }, [series]);

  if (metrics.length < 2 || series.length === 0) {
    return null; // Radar needs at least 2 axes and 1 series
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="metric" fontSize={12} />
            <PolarRadiusAxis angle={90} domain={[0, 1]} tickCount={6} fontSize={10} />
            {series.map((s, i) => (
              <Radar
                key={s.name}
                name={s.name}
                dataKey={s.name}
                stroke={COLORS[i % COLORS.length]}
                fill={COLORS[i % COLORS.length]}
                fillOpacity={0.15}
              />
            ))}
            <Legend />
            <Tooltip formatter={(value) => `${(Number(value) * 100).toFixed(0)}%`} />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
