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
import type { Result, Score } from '@/types';

interface ResultDetailViewProps {
  result: Result;
  evaluationName?: string;
  evaluationMode?: string;
}

function DimensionBadges({ dimensions }: { dimensions: Record<string, number> | undefined }) {
  const entries = Object.entries(dimensions ?? {});
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

function JudgeReasoning({ reasoning }: { reasoning: string | undefined }) {
  const [expanded, setExpanded] = useState(false);
  const maxLength = 100;
  const text = reasoning ?? '';

  if (text.length <= maxLength) {
    return <span className="text-sm">{text}</span>;
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

const EMPTY_METRICS = {
  total_items: 0,
  passed_items: 0,
  failed_items: 0,
  mean_score: 0,
  median_score: 0,
  pass_rate: 0,
  score_distribution: {},
};

export function ResultDetailView({ result, evaluationName, evaluationMode }: ResultDetailViewProps) {
  const metrics = result.aggregate_metrics ?? EMPTY_METRICS;
  const scores = result.scores ?? [];

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
            <Badge variant={result.status === 'completed' ? 'default' : 'destructive'}>
              {result.status}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-sm text-muted-foreground">Total Items</p>
              <p className="text-2xl font-bold">{metrics.total_items}</p>
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
        <ScoreDistributionChart scores={scores} />
        <PassFailChart passedItems={metrics.passed_items} failedItems={metrics.failed_items} />
      </div>

      {/* Per-Item Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Per-Item Results</CardTitle>
        </CardHeader>
        <CardContent>
          {scores.length === 0 ? (
            <p className="text-muted-foreground py-4 text-center">No individual scores available.</p>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item ID</TableHead>
                    <TableHead>Overall Score</TableHead>
                    <TableHead>Pass/Fail</TableHead>
                    <TableHead>Dimensions</TableHead>
                    <TableHead>Judge Reasoning</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scores.map((score: Score) => (
                    <TableRow key={score.item_id}>
                      <TableCell className="font-mono text-sm">{score.item_id}</TableCell>
                      <TableCell>{score.overall.toFixed(3)}</TableCell>
                      <TableCell>
                        {score.pass ? (
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell>
                        <DimensionBadges dimensions={score.dimensions} />
                      </TableCell>
                      <TableCell className="max-w-xs">
                        <JudgeReasoning reasoning={score.judge_reasoning} />
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
