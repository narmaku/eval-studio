import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ArenaContestantSummary } from '@/types';

const COLORS = [
  'hsl(210, 80%, 55%)',
  'hsl(340, 75%, 55%)',
  'hsl(150, 65%, 45%)',
  'hsl(45, 90%, 50%)',
  'hsl(270, 60%, 55%)',
  'hsl(15, 80%, 55%)',
];

interface ContestantScoreChartProps {
  contestants: ArenaContestantSummary[];
}

export function ContestantScoreChart({ contestants }: ContestantScoreChartProps) {
  if (contestants.length === 0) return null;

  const data = contestants.map((c) => ({
    name: c.contestant_model,
    score: c.average_score,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Contestant Score Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
            <XAxis
              type="number"
              domain={[0, 1]}
              tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            />
            <YAxis type="category" dataKey="name" width={150} fontSize={12} />
            <Tooltip formatter={(value: number) => `${(value * 100).toFixed(0)}%`} />
            <Bar dataKey="score" radius={[0, 4, 4, 0]}>
              {data.map((_entry, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
