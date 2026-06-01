import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { ArenaLeaderboardResponse, ArenaContestantSummary } from '@/types';

interface ArenaLeaderboardProps {
  leaderboard: ArenaLeaderboardResponse;
}

function scoreColorClass(score: number): string {
  if (score >= 0.7) return 'text-green-600 dark:text-green-400';
  if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function isFullyErrored(contestant: ArenaContestantSummary): boolean {
  return contestant.errored_count === contestant.total_items && contestant.total_items > 0;
}

export function ArenaLeaderboard({ leaderboard }: ArenaLeaderboardProps) {
  const { contestants } = leaderboard;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Leaderboard</CardTitle>
      </CardHeader>
      <CardContent>
        {contestants.length === 0 ? (
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
                    <TableCell className="font-medium">
                      {contestant.contestant_model}
                    </TableCell>
                    <TableCell>
                      {allErrored ? (
                        <Badge variant="destructive">Error</Badge>
                      ) : (
                        <span className={`font-semibold tabular-nums ${scoreColorClass(contestant.average_score)}`}>
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
        )}
      </CardContent>
    </Card>
  );
}
