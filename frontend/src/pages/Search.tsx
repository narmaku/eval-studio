import { useEffect, useMemo, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { BarChart3, MessageSquare, Database } from 'lucide-react';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useSessionHistoryStore } from '@/stores/sessionHistoryStore';
import { useDatasetStore } from '@/stores/datasetStore';
import { getModeLabel, formatMonoDate } from '@/lib/designUtils';
import { cn } from '@/lib/utils';
import type { SearchResult } from '@/stores/searchStore';

type FilterType = 'all' | 'evaluations' | 'sessions' | 'datasets';

const filterOptions: { value: FilterType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'evaluations', label: 'Evaluations' },
  { value: 'sessions', label: 'Sessions' },
  { value: 'datasets', label: 'Datasets' },
];

const typeIcons: Record<SearchResult['type'], React.ComponentType<{ className?: string }>> = {
  evaluation: BarChart3,
  session: MessageSquare,
  dataset: Database,
};

const typeLabels: Record<SearchResult['type'], string> = {
  evaluation: 'Evaluation',
  session: 'Session',
  dataset: 'Dataset',
};

export default function Search() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryParam = searchParams.get('q') ?? '';
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');

  const { evaluations, fetchEvaluations } = useEvaluationStore();
  const { sessions, fetchSessions } = useSessionHistoryStore();
  const { datasets, fetchDatasets } = useDatasetStore();

  // Fetch data on mount if stores are empty
  useEffect(() => {
    if (evaluations.length === 0) void fetchEvaluations();
    if (sessions.length === 0) void fetchSessions();
    if (datasets.length === 0) void fetchDatasets();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const allResults = useMemo(() => {
    if (!queryParam.trim()) return [];

    const lowerQuery = queryParam.toLowerCase();

    const evalResults: SearchResult[] = evaluations
      .filter((e) => e.name.toLowerCase().includes(lowerQuery))
      .map((e) => ({
        id: e.id,
        type: 'evaluation' as const,
        name: e.name,
        subtitle: `${getModeLabel(e.mode)} · ${e.status} · ${formatMonoDate(e.created_at)}`,
        path: `/results/${e.id}`,
      }));

    const sessionResults: SearchResult[] = sessions
      .filter((s) => (s.name ?? '').toLowerCase().includes(lowerQuery))
      .map((s) => ({
        id: s.id,
        type: 'session' as const,
        name: s.name ?? `Session ${s.id.slice(0, 8)}`,
        subtitle: `${getModeLabel(s.mode)} · ${s.status} · ${formatMonoDate(s.created_at)}`,
        path: `/sessions/${s.id}`,
      }));

    const datasetResults: SearchResult[] = datasets
      .filter((d) => d.name.toLowerCase().includes(lowerQuery))
      .map((d) => ({
        id: d.id,
        type: 'dataset' as const,
        name: d.name,
        subtitle: `${d.format} · ${d.item_count} items · ${formatMonoDate(d.created_at)}`,
        path: `/datasets`,
      }));

    return [...evalResults, ...sessionResults, ...datasetResults];
  }, [queryParam, evaluations, sessions, datasets]);

  const filteredResults = useMemo(() => {
    if (activeFilter === 'all') return allResults;

    const typeMap: Record<FilterType, SearchResult['type'] | null> = {
      all: null,
      evaluations: 'evaluation',
      sessions: 'session',
      datasets: 'dataset',
    };

    const targetType = typeMap[activeFilter];
    return allResults.filter((r) => r.type === targetType);
  }, [allResults, activeFilter]);

  // Group results by type for display
  const groupedResults = useMemo(() => {
    const groups: Record<SearchResult['type'], SearchResult[]> = {
      evaluation: [],
      session: [],
      dataset: [],
    };

    for (const result of filteredResults) {
      groups[result.type].push(result);
    }

    return groups;
  }, [filteredResults]);

  const handleResultClick = (result: SearchResult) => {
    navigate(result.path);
  };

  return (
    <div className="mx-auto max-w-[900px] px-8 py-8">
      {/* Header */}
      <h1 className="text-[25px] font-semibold tracking-[-0.02em] text-foreground">Search</h1>

      {queryParam && (
        <p className="mt-1 text-[13px] text-text-2">
          Showing results for &ldquo;{queryParam}&rdquo;
        </p>
      )}

      {/* Filter pills */}
      <div className="mt-5 inline-flex gap-0.5 rounded-[10px] bg-surface-2 p-1">
        {filterOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => setActiveFilter(option.value)}
            className={cn(
              'cursor-pointer rounded-[7px] px-3 py-1.5 text-[12.5px] transition-colors',
              activeFilter === option.value
                ? 'bg-surface-3 font-medium text-foreground'
                : 'text-text-2 hover:bg-surface-3',
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* Results */}
      <div className="mt-6 space-y-6">
        {!queryParam && (
          <p className="py-8 text-center text-[13px] text-text-3">
            Enter a search term to find evaluations, sessions, and datasets.
          </p>
        )}

        {queryParam && filteredResults.length === 0 && (
          <p className="py-8 text-center text-[13px] text-text-3">
            No results found for &ldquo;{queryParam}&rdquo;
          </p>
        )}

        {(['evaluation', 'session', 'dataset'] as const).map((type) => {
          const items = groupedResults[type];
          if (items.length === 0) return null;

          return (
            <div key={type}>
              <h2 className="mb-2 text-[12px] font-medium uppercase tracking-wide text-text-3">
                {typeLabels[type]}s ({items.length})
              </h2>
              <div className="overflow-hidden rounded-[12px] border border-border bg-card">
                {items.map((result, idx) => {
                  const Icon = typeIcons[result.type];
                  return (
                    <button
                      key={`${result.type}-${result.id}`}
                      onClick={() => handleResultClick(result)}
                      className={cn(
                        'flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-3',
                        idx > 0 && 'border-t border-border',
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0 text-text-3" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[14px] font-medium text-foreground">
                          {result.name}
                        </div>
                        <div className="truncate text-[12px] text-text-3">{result.subtitle}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
