import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { HashIcon, CheckCircleIcon, BarChartIcon, TrendingUpIcon } from 'lucide-react';
import type { AggregateMetrics } from '@/types';

interface AggregateStatsProps {
  metrics: AggregateMetrics;
}

const PASS_COLOR = '#22c55e';
const FAIL_COLOR = '#ef4444';
const BAR_COLOR = '#6b7280';

export function AggregateStats({ metrics }: AggregateStatsProps) {
  const passFailData = useMemo(
    () => [
      { name: 'Pass', value: metrics.passed_items },
      { name: 'Fail', value: metrics.failed_items },
    ],
    [metrics.passed_items, metrics.failed_items],
  );

  const distributionData = useMemo(() => {
    return Object.entries(metrics.score_distribution)
      .map(([bucket, count]) => ({
        bucket,
        count,
      }))
      .sort((a, b) => a.bucket.localeCompare(b.bucket));
  }, [metrics.score_distribution]);

  return (
    <div className="grid gap-4 md:grid-cols-4">
      {/* Total Items */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Items</CardTitle>
          <HashIcon className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.total_items}</div>
        </CardContent>
      </Card>

      {/* Pass Rate */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
          <CheckCircleIcon className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold">
              {(metrics.pass_rate * 100).toFixed(0)}%
            </span>
            <div className="h-[60px] w-[60px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={passFailData}
                    cx="50%"
                    cy="50%"
                    innerRadius={18}
                    outerRadius={28}
                    dataKey="value"
                    strokeWidth={0}
                  >
                    <Cell fill={PASS_COLOR} />
                    <Cell fill={FAIL_COLOR} />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Mean Score */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Mean Score</CardTitle>
          <TrendingUpIcon className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.mean_score.toFixed(2)}</div>
          <p className="text-xs text-muted-foreground">
            Median: {metrics.median_score.toFixed(2)}
          </p>
        </CardContent>
      </Card>

      {/* Score Distribution */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Distribution</CardTitle>
          <BarChartIcon className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="h-[60px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distributionData}>
                <XAxis dataKey="bucket" hide />
                <YAxis hide />
                <Bar dataKey="count" fill={BAR_COLOR} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
