import { useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { RadarComparisonChart } from '@/components/results';
import { useResultStore } from '@/stores/resultStore';
import type { EvaluationComparisonItem, CrossEvaluationItemComparison } from '@/types';

function LeaderboardTable({
  evaluations,
  referenceId,
}: {
  evaluations: EvaluationComparisonItem[];
  referenceId: string | null;
}) {
  // Sort by average_score descending
  const sorted = useMemo(
    () => [...evaluations].sort((a, b) => b.average_score - a.average_score),
    [evaluations],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Leaderboard</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Rank</TableHead>
              <TableHead>Evaluation</TableHead>
              <TableHead>Mean Score</TableHead>
              <TableHead>Pass Rate</TableHead>
              <TableHead>Items</TableHead>
              <TableHead>Passed</TableHead>
              <TableHead>Failed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((evaluation, index) => {
              const isRef = evaluation.evaluation_id === referenceId;
              const passRate =
                evaluation.total_items > 0
                  ? ((evaluation.passed_count / evaluation.total_items) * 100).toFixed(1)
                  : '0.0';

              return (
                <TableRow
                  key={evaluation.evaluation_id}
                  className={isRef ? 'bg-yellow-50 dark:bg-yellow-950/20' : ''}
                >
                  <TableCell className="font-medium">#{index + 1}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {evaluation.evaluation_name}
                      {isRef && (
                        <Badge variant="outline" className="text-xs">
                          Reference
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{evaluation.average_score.toFixed(3)}</TableCell>
                  <TableCell>{passRate}%</TableCell>
                  <TableCell>{evaluation.total_items}</TableCell>
                  <TableCell>{evaluation.passed_count}</TableCell>
                  <TableCell>{evaluation.failed_count}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function PerItemComparisonGrid({
  itemComparisons,
  evaluations,
}: {
  itemComparisons: CrossEvaluationItemComparison[];
  evaluations: EvaluationComparisonItem[];
}) {
  // Build a lookup from evaluation_id -> name
  const evalNames = useMemo(() => {
    const map = new Map<string, string>();
    evaluations.forEach((e) => map.set(e.evaluation_id, e.evaluation_name));
    return map;
  }, [evaluations]);

  if (itemComparisons.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Per-Item Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {itemComparisons.map((item) => (
            <Card key={item.dataset_item_id} className="border-dashed">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-mono">{item.dataset_item_id}</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Evaluation</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Passed</TableHead>
                      <TableHead>Answer</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {item.results.map((result) => (
                      <TableRow key={result.id}>
                        <TableCell className="font-medium">
                          {evalNames.get(result.evaluation_id) ?? result.evaluation_id}
                        </TableCell>
                        <TableCell>
                          {result.score !== null ? result.score.toFixed(3) : 'N/A'}
                        </TableCell>
                        <TableCell>
                          <Badge variant={result.passed ? 'default' : 'destructive'}>
                            {result.passed ? 'Pass' : 'Fail'}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {result.actual_answer ?? 'N/A'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function ResultComparison() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const evaluationIds = searchParams.getAll('ids');
  const referenceId = searchParams.get('ref');

  const comparisonData = useResultStore((s) => s.comparisonData);
  const isLoading = useResultStore((s) => s.isLoading);
  const error = useResultStore((s) => s.error);
  const fetchComparison = useResultStore((s) => s.fetchComparison);

  useEffect(() => {
    if (evaluationIds.length >= 2) {
      void fetchComparison(evaluationIds, referenceId ?? undefined);
    }
    // Only run on mount / when URL params change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.toString()]);

  // Build radar chart series from comparison data
  const radarSeries = useMemo(() => {
    if (!comparisonData) return [];
    return comparisonData.evaluations
      .map((evalItem) => {
        // Compute per-evaluation radar data from aggregate metrics
        const passRate =
          evalItem.total_items > 0 ? evalItem.passed_count / evalItem.total_items : 0;
        return {
          name: evalItem.evaluation_name,
          data: {
            'Mean Score': evalItem.average_score,
            'Pass Rate': passRate,
          } as Record<string, number>,
        };
      })
      .filter((s) => Object.keys(s.data).length > 0);
  }, [comparisonData]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/results')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Results
        </Button>
      </div>

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Evaluation Comparison</h1>
        <p className="text-muted-foreground">
          Comparing {evaluationIds.length} evaluations side by side.
        </p>
      </div>
      <Separator />

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading comparison data...</p>
        </div>
      )}

      {error && !isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <p className="text-destructive font-medium">Error loading comparison</p>
            <p className="text-muted-foreground text-sm">{error}</p>
          </div>
        </div>
      )}

      {comparisonData && !isLoading && !error && (
        <div className="space-y-6">
          <LeaderboardTable
            evaluations={comparisonData.evaluations}
            referenceId={comparisonData.reference_evaluation_id}
          />

          {radarSeries.length >= 1 && (
            <RadarComparisonChart series={radarSeries} title="Metric Comparison" />
          )}

          <PerItemComparisonGrid
            itemComparisons={comparisonData.item_comparisons}
            evaluations={comparisonData.evaluations}
          />
        </div>
      )}
    </div>
  );
}
