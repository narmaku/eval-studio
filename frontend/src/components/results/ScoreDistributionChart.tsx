import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { bucketScores } from './scoreUtils';
import type { Result } from '@/types';

interface ScoreDistributionChartProps {
  results: Result[];
}

export function ScoreDistributionChart({ results }: ScoreDistributionChartProps) {
  const data = useMemo(() => bucketScores(results), [results]);

  if (results.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Score Distribution</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <p className="text-muted-foreground">No score data available.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <XAxis dataKey="label" fontSize={12} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
