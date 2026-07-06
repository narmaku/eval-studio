import { useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, ArrowRight } from 'lucide-react';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useDatasetStore } from '@/stores/datasetStore';
import { useSessionHistoryStore } from '@/stores/sessionHistoryStore';
import {
  getScoreColorClass,
  getModeBadgeClasses,
  getModeLabel,
  getStatusPillClasses,
  formatMonoDate,
} from '@/lib/designUtils';
import { cn } from '@/lib/utils';

function StatTile({
  label,
  value,
  sub,
  dotColor,
  valueClass,
}: {
  label: string;
  value: string;
  sub: string;
  dotColor: string;
  valueClass?: string;
}) {
  return (
    <div className="relative rounded-[13px] border border-border bg-card p-4 shadow-sm">
      <span className={cn('absolute top-4 right-4 h-2 w-2 rounded-full', dotColor)} />
      <p className="text-[12px] font-[520] text-text-2">{label}</p>
      <p className={cn('mt-1 font-mono text-[26px] font-semibold tabular-nums', valueClass)}>
        {value}
      </p>
      <p className="mt-0.5 font-mono text-[11px] text-text-3">{sub}</p>
    </div>
  );
}

function PassRateSparkline({ rates }: { rates: number[] }) {
  if (rates.length === 0) return null;
  const max = Math.max(...rates, 0.01);

  return (
    <div className="flex items-end gap-[3px] h-[80px]">
      {rates.map((rate, i) => {
        const heightPct = (rate / max) * 100;
        const isLast = i === rates.length - 1;
        return (
          <div
            key={i}
            className={cn(
              'flex-1 rounded-t-sm min-h-[4px] transition-all',
              isLast ? 'bg-accent' : 'bg-accent/[0.34]',
            )}
            style={{ height: `${Math.max(heightPct, 5)}%` }}
            title={`${(rate * 100).toFixed(0)}%`}
          />
        );
      })}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { evaluations, fetchEvaluations } = useEvaluationStore();
  const { datasets, fetchDatasets } = useDatasetStore();
  const { sessions, fetchSessions } = useSessionHistoryStore();

  useEffect(() => {
    void fetchEvaluations();
    void fetchDatasets();
    void fetchSessions();
  }, [fetchEvaluations, fetchDatasets, fetchSessions]);

  const completedEvals = useMemo(
    () => evaluations.filter((e) => e.status === 'completed'),
    [evaluations],
  );

  const stats = useMemo(() => {
    const avgPassRate =
      completedEvals.length > 0
        ? completedEvals.reduce((sum, e) => sum + (e.pass_rate ?? 0), 0) / completedEvals.length
        : 0;

    const totalItems = datasets.reduce((sum, d) => sum + (d.item_count ?? 0), 0);
    const unscoredSessions = sessions.filter(
      (s) => s.status === 'ended' && (!s.scores || !s.scores.overall),
    ).length;

    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const recentEvals = evaluations.filter((e) => new Date(e.created_at) > weekAgo).length;

    return { avgPassRate, totalItems, unscoredSessions, recentEvals };
  }, [completedEvals, datasets, sessions, evaluations]);

  const recentEvaluations = useMemo(
    () =>
      [...evaluations]
        .filter((e) => e.status === 'completed' || e.status === 'failed')
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 6),
    [evaluations],
  );

  const passRates = useMemo(() => {
    const sorted = [...completedEvals]
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .slice(-14);
    return sorted.map((e) => e.pass_rate ?? 0);
  }, [completedEvals]);

  const recentSessions = useMemo(
    () =>
      [...sessions]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5),
    [sessions],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[25px] font-semibold tracking-[-0.02em]">Dashboard</h1>
          <p className="text-[13px] text-text-2">
            Everything you're building, running, and improving — at a glance.
          </p>
        </div>
        <Link
          to="/evaluate"
          className="flex items-center gap-2 rounded-[9px] bg-primary px-4 py-2.5 text-[13px] font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          New Evaluation
        </Link>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-4 gap-3">
        <StatTile
          label="Evaluations"
          value={String(evaluations.length)}
          sub={`${stats.recentEvals} this week`}
          dotColor="bg-accent"
        />
        <StatTile
          label="Avg pass rate"
          value={`${(stats.avgPassRate * 100).toFixed(1)}%`}
          sub={completedEvals.length > 0 ? `${completedEvals.length} completed` : 'no data'}
          dotColor="bg-pass"
          valueClass="text-pass"
        />
        <StatTile
          label="Datasets"
          value={String(datasets.length)}
          sub={`${stats.totalItems.toLocaleString()} items`}
          dotColor="bg-text-3"
        />
        <StatTile
          label="Sessions"
          value={String(sessions.length)}
          sub={stats.unscoredSessions > 0 ? `${stats.unscoredSessions} unscored` : 'all scored'}
          dotColor="bg-warn"
        />
      </div>

      {/* Two-column body */}
      <div className="grid gap-4" style={{ gridTemplateColumns: '1.55fr 1fr' }}>
        {/* Recent evaluations */}
        <div className="rounded-[14px] border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[14px] font-semibold">Recent evaluations</h2>
            <Link
              to="/results"
              className="flex items-center gap-1 text-[12px] font-medium text-accent hover:underline"
            >
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="flex flex-col">
            {recentEvaluations.length === 0 && (
              <p className="py-8 text-center text-[12.5px] text-text-3">
                No evaluations yet. Start your first one!
              </p>
            )}
            {recentEvaluations.map((ev) => (
              <button
                key={ev.id}
                onClick={() => navigate(`/results/${ev.id}`)}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-surface-3"
              >
                <span
                  className={cn(
                    'shrink-0 rounded-[6px] px-2 py-0.5 text-[10px] font-semibold uppercase',
                    getModeBadgeClasses(ev.mode ?? 'qa'),
                  )}
                >
                  {getModeLabel(ev.mode ?? 'qa')}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-[13px] font-medium">{ev.name}</p>
                  <p className="font-mono text-[10.5px] text-text-3">
                    {ev.result_count ?? 0} items · {formatMonoDate(ev.created_at)} ·{' '}
                    <span className={getStatusPillClasses(ev.status).replace(/bg-\S+/g, '')}>
                      {ev.status}
                    </span>
                  </p>
                </div>
                <div className="text-right shrink-0">
                  {ev.status === 'completed' && ev.average_score != null ? (
                    <>
                      <p
                        className={cn(
                          'font-mono text-[14px] font-semibold tabular-nums',
                          getScoreColorClass(ev.average_score),
                        )}
                      >
                        {ev.average_score.toFixed(3)}
                      </p>
                      <p className="font-mono text-[10px] text-text-3">
                        {((ev.pass_rate ?? 0) * 100).toFixed(0)}% pass
                      </p>
                    </>
                  ) : (
                    <p className="font-mono text-[12px] text-text-3">—</p>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4">
          {/* Pass rate sparkline */}
          <div className="rounded-[14px] border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[14px] font-semibold">Pass rate</h2>
              {completedEvals.length > 1 && (
                <span className="font-mono text-[11px] text-text-3">
                  {completedEvals.length} runs
                </span>
              )}
            </div>
            {passRates.length > 0 ? (
              <>
                <PassRateSparkline rates={passRates} />
                <div className="mt-2 flex justify-between font-mono text-[10px] text-text-3">
                  <span>oldest</span>
                  <span>latest</span>
                </div>
              </>
            ) : (
              <p className="py-6 text-center text-[12px] text-text-3">
                Complete evaluations to see trends
              </p>
            )}
          </div>

          {/* Recent sessions */}
          <div className="rounded-[14px] border border-border bg-card p-5 shadow-sm">
            <h2 className="text-[14px] font-semibold mb-3">Recent sessions</h2>
            <div className="flex flex-col">
              {recentSessions.length === 0 && (
                <p className="py-4 text-center text-[12px] text-text-3">No sessions yet</p>
              )}
              {recentSessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => navigate(`/sessions/${s.id}`)}
                  className="flex items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-3"
                >
                  <span
                    className={cn(
                      'h-2 w-2 shrink-0 rounded-full',
                      s.scores?.overall != null ? 'bg-pass' : 'bg-text-3',
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-[13px] font-medium">{s.name ?? s.id.slice(0, 8)}</p>
                    <p className="font-mono text-[10.5px] text-text-3">
                      {formatMonoDate(s.created_at)}
                    </p>
                  </div>
                  <span
                    className={cn(
                      'font-mono text-[13px] font-semibold tabular-nums',
                      s.scores?.overall != null
                        ? getScoreColorClass(s.scores.overall)
                        : 'text-text-3',
                    )}
                  >
                    {s.scores?.overall != null ? `${Math.round(s.scores.overall * 100)}%` : '—'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
