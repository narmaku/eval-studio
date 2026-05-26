import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react';
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
import { ScoreDistributionChart } from './ScoreDistributionChart';
import { PassFailChart } from './PassFailChart';
import type { Result, AggregateMetrics } from '@/types';

interface ResultDetailViewProps {
  results: Result[];
  aggregateMetrics?: AggregateMetrics | null;
  evaluationName?: string;
  evaluationMode?: string;
}

function ScoreBreakdownBadges({ breakdown }: { breakdown: Record<string, number> | null | undefined }) {
  const entries = Object.entries(breakdown ?? {});
  if (entries.length === 0) {
    return <span className="text-muted-foreground">--</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([key, value]) => (
        <Badge key={key} variant="outline" className="text-xs">
          {key}: {value.toFixed(2)}
        </Badge>
      ))}
    </div>
  );
}

function JudgeReasoning({ reasoning }: { reasoning: string | null | undefined }) {
  const [expanded, setExpanded] = useState(false);
  const text = reasoning ?? '';
  const maxLength = 100;

  if (text.length <= maxLength) {
    return <span className="text-sm">{text || '--'}</span>;
  }

  return (
    <span className="text-sm">
      {expanded ? text : `${text.slice(0, maxLength)}...`}
      <button
        className="ml-1 text-primary underline text-xs"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        {expanded ? 'less' : 'more'}
      </button>
    </span>
  );
}

const EMPTY_METRICS: AggregateMetrics = {
  total_items: 0,
  passed_items: 0,
  failed_items: 0,
  mean_score: 0,
  median_score: 0,
  pass_rate: 0,
  score_distribution: {},
};

export function ResultDetailView({ results, aggregateMetrics, evaluationName, evaluationMode }: ResultDetailViewProps) {
  const metrics = aggregateMetrics ?? EMPTY_METRICS;

  return (
    <div className="space-y-6">
      <Link to="/results" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Back to Results
      </Link>

      {/* Summary Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            {evaluationName ?? 'Evaluation Result'}
            {evaluationMode && (
              <Badge variant="outline" className="text-xs">
                {evaluationMode.toUpperCase()}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-sm text-muted-foreground">Total Items</p>
              <p className="text-2xl font-bold">{metrics.total_items || results.length}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Pass Rate</p>
              <p className="text-2xl font-bold">{(metrics.pass_rate * 100).toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Mean Score</p>
              <p className="text-2xl font-bold">{metrics.mean_score.toFixed(3)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Median Score</p>
              <p className="text-2xl font-bold">{metrics.median_score.toFixed(3)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <ScoreDistributionChart results={results} />
        <PassFailChart passedItems={metrics.passed_items} failedItems={metrics.failed_items} />
      </div>

      {/* Per-Item Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Per-Item Results</CardTitle>
        </CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <p className="text-muted-foreground py-4 text-center">No individual results available.</p>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Pass/Fail</TableHead>
                    <TableHead>Breakdown</TableHead>
                    <TableHead>Judge Reasoning</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-mono text-sm">{r.dataset_item_id?.slice(0, 8) ?? '--'}</TableCell>
                      <TableCell>{r.score != null ? r.score.toFixed(3) : '--'}</TableCell>
                      <TableCell>
                        {r.passed === true ? (
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                        ) : r.passed === false ? (
                          <XCircle className="h-5 w-5 text-red-500" />
                        ) : (
                          <span className="text-muted-foreground">--</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <ScoreBreakdownBadges breakdown={r.scores_breakdown} />
                      </TableCell>
                      <TableCell className="max-w-xs">
                        <JudgeReasoning reasoning={r.judge_reasoning} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
