import { create } from 'zustand';
import { useEvaluationStore } from '@/stores/evaluationStore';
import { useSessionHistoryStore } from '@/stores/sessionHistoryStore';
import { useDatasetStore } from '@/stores/datasetStore';
import { getModeLabel, formatMonoDate } from '@/lib/designUtils';

export interface SearchResult {
  id: string;
  type: 'evaluation' | 'session' | 'dataset';
  name: string;
  subtitle: string;
  path: string;
}

interface SearchStore {
  query: string;
  isOpen: boolean;
  results: SearchResult[];
  setQuery: (query: string) => void;
  setOpen: (open: boolean) => void;
  search: (query: string) => void;
  clear: () => void;
}

const MAX_RESULTS = 8;

export const useSearchStore = create<SearchStore>((set) => ({
  query: '',
  isOpen: false,
  results: [],

  setQuery: (query: string) => set({ query }),

  setOpen: (open: boolean) => set({ isOpen: open }),

  search: (query: string) => {
    if (!query.trim()) {
      set({ results: [] });
      return;
    }

    const lowerQuery = query.toLowerCase();

    const evaluations = useEvaluationStore.getState().evaluations;
    const sessions = useSessionHistoryStore.getState().sessions;
    const datasets = useDatasetStore.getState().datasets;

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

    // Interleave results by type for a balanced mix, limited to MAX_RESULTS
    const allResults: SearchResult[] = [];
    const sources = [evalResults, sessionResults, datasetResults];
    let idx = 0;
    while (allResults.length < MAX_RESULTS) {
      let added = false;
      for (const source of sources) {
        const item = source[idx];
        if (item && allResults.length < MAX_RESULTS) {
          allResults.push(item);
          added = true;
        }
      }
      if (!added) break;
      idx++;
    }

    set({ results: allResults });
  },

  clear: () => set({ query: '', results: [], isOpen: false }),
}));
