import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Score } from '@/types';

interface ScoreDistributionChartProps {
  scores: Score[];
}

interface Bucket {
  label: string;
  count: number;
}

const BUCKET_LABELS = [
  '0.0-0.1',
  '0.1-0.2',
  '0.2-0.3',
  '0.3-0.4',
  '0.4-0.5',
  '0.5-0.6',
  '0.6-0.7',
  '0.7-0.8',
  '0.8-0.9',
  '0.9-1.0',
];

export function bucketScores(scores: Score[]): Bucket[] {
  const counts = new Array<number>(10).fill(0);

  for (const score of scores) {
    const index = Math.min(Math.floor(score.overall * 10), 9);
    counts[index]!++;
  }

  return BUCKET_LABELS.map((label, i) => ({
    label,
    count: counts[i]!,
  }));
}

export function ScoreDistributionChart({ scores }: ScoreDistributionChartProps) {
  const data = useMemo(() => bucketScores(scores), [scores]);

  if (scores.length === 0) {
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
