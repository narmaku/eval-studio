import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { BarChart3 } from 'lucide-react';
import type { SessionScore } from '@/types';

interface ScoringPanelProps {
  scores: SessionScore[];
  isSessionEnded: boolean;
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const percentage = Math.round(value * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium capitalize">{label}</span>
        <span className="text-muted-foreground">{percentage}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className="h-2 rounded-full bg-primary transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export function ScoringPanel({ scores, isSessionEnded }: ScoringPanelProps) {
  const sessionScores = scores.filter((s) => s.turn_number === null);
  const turnScores = scores.filter((s) => s.turn_number !== null);

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <BarChart3 className="h-4 w-4" />
          Scores
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto p-4">
        {scores.length === 0 && !isSessionEnded && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              Scores will appear after the session ends.
            </p>
          </div>
        )}

        {scores.length === 0 && isSessionEnded && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">Waiting for judge scoring...</p>
          </div>
        )}

        {/* Session-level scores */}
        {sessionScores.map((score, idx) => (
          <div key={`session-${idx}`} className="space-y-3">
            <div className="text-center">
              <p className="text-xs font-medium text-muted-foreground mb-1">Overall Score</p>
              <p className="text-4xl font-bold">{Math.round(score.overall * 100)}%</p>
            </div>

            <Separator />

            <div className="space-y-2">
              {Object.entries(score.dimensions).map(([dim, val]) => (
                <ScoreBar key={dim} label={dim} value={val} />
              ))}
            </div>

            {score.judge_reasoning && (
              <>
                <Separator />
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Judge Reasoning</p>
                  <blockquote className="border-l-2 pl-3 text-xs text-muted-foreground italic">
                    {score.judge_reasoning}
                  </blockquote>
                </div>
              </>
            )}
          </div>
        ))}

        {/* Turn-level scores */}
        {turnScores.length > 0 && (
          <>
            {sessionScores.length > 0 && <Separator className="my-4" />}
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground">Per-Turn Scores</p>
              {turnScores.map((score, idx) => (
                <div key={`turn-${idx}`} className="rounded-lg border p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium">Turn {score.turn_number}</span>
                    <span className="text-xs text-muted-foreground">
                      {Math.round(score.overall * 100)}%
                    </span>
                  </div>
                  {Object.entries(score.dimensions).map(([dim, val]) => (
                    <ScoreBar key={dim} label={dim} value={val} />
                  ))}
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
