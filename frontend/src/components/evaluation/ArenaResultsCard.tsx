import { useState, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { cn } from '@/lib/utils';
import type { ArenaLeaderboardResponse, ArenaContestantSummary } from '@/types';

const CHART_COLORS = [
  'hsl(210, 80%, 55%)',
  'hsl(340, 75%, 55%)',
  'hsl(150, 65%, 45%)',
  'hsl(45, 90%, 50%)',
  'hsl(270, 60%, 55%)',
  'hsl(15, 80%, 55%)',
];

function scoreColorClass(score: number): string {
  if (score >= 0.7) return 'text-green-600 dark:text-green-400';
  if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function isFullyErrored(contestant: ArenaContestantSummary): boolean {
  return contestant.errored_count === contestant.total_items && contestant.total_items > 0;
}

interface ArenaResultsCardProps {
  leaderboard: ArenaLeaderboardResponse;
  className?: string;
}

type ArenaTab = 'leaderboard' | 'scores';

export function ArenaResultsCard({
  leaderboard,
  className,
}: ArenaResultsCardProps): React.JSX.Element {
  const [activeTab, setActiveTab] = useState<ArenaTab>('leaderboard');
  const { contestants } = leaderboard;

  const chartData = useMemo(
    () =>
      contestants.map((c) => ({
        name: c.contestant_model,
        score: c.average_score,
      })),
    [contestants],
  );

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-1 rounded-lg bg-muted p-0.5">
          <button
            type="button"
            className={cn(
              'flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
              activeTab === 'leaderboard'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setActiveTab('leaderboard')}
          >
            Leaderboard
          </button>
          <button
            type="button"
            className={cn(
              'flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
              activeTab === 'scores'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setActiveTab('scores')}
          >
            Scores
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {activeTab === 'leaderboard' ? (
          /* Leaderboard table (inline, no nested card) */
          contestants.length === 0 ? (
            <p className="text-sm text-muted-foreground">No contestants to display.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rank</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Avg Score</TableHead>
                  <TableHead>Passed</TableHead>
                  <TableHead>Failed</TableHead>
                  <TableHead>Errored</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contestants.map((contestant, index) => {
                  const rank = index + 1;
                  const isFirst = rank === 1;
                  const allErrored = isFullyErrored(contestant);

                  return (
                    <TableRow
                      key={contestant.contestant_model}
                      className={isFirst ? 'bg-yellow-50 dark:bg-yellow-900/10' : ''}
                    >
                      <TableCell>
                        <Badge variant={isFirst ? 'default' : 'secondary'}>{rank}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{contestant.contestant_model}</TableCell>
                      <TableCell>
                        {allErrored ? (
                          <Badge variant="destructive">Error</Badge>
                        ) : (
                          <span
                            className={`font-semibold tabular-nums ${scoreColorClass(contestant.average_score)}`}
                          >
                            {Math.round(contestant.average_score * 100)}%
                          </span>
                        )}
                      </TableCell>
                      <TableCell>{contestant.passed_count}</TableCell>
                      <TableCell>{contestant.failed_count}</TableCell>
                      <TableCell>{contestant.errored_count}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )
        ) : /* Scores chart (inline, no nested card) */
        contestants.length === 0 ? null : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
              <XAxis
                type="number"
                domain={[0, 1]}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
              />
              <YAxis type="category" dataKey="name" width={150} fontSize={12} />
              <Tooltip formatter={(value) => `${(Number(value) * 100).toFixed(0)}%`} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {chartData.map((_entry, index) => (
                  <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
