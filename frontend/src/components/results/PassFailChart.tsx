import { useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PassFailChartProps {
  passedItems: number;
  failedItems: number;
}

const COLORS = {
  passed: '#22c55e',
  failed: '#ef4444',
};

export function PassFailChart({ passedItems, failedItems }: PassFailChartProps) {
  const data = useMemo(
    () => [
      { name: 'Passed', value: passedItems },
      { name: 'Failed', value: failedItems },
    ],
    [passedItems, failedItems],
  );

  const total = passedItems + failedItems;

  if (total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pass / Fail</CardTitle>
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
        <CardTitle>Pass / Fail</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
              label={({ name, value }) => `${name}: ${value}`}
            >
              <Cell fill={COLORS.passed} />
              <Cell fill={COLORS.failed} />
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
