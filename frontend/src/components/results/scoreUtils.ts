import type { Result } from '@/types';

export interface Bucket {
  label: string;
  count: number;
}

const BUCKET_LABELS = [
  '0.0-0.1',
  '0.1-0.2',
  '0.2-0.3',
  '0.3-0.4',
  '0.4-0.5',
  '0.5-0.6',
  '0.6-0.7',
  '0.7-0.8',
  '0.8-0.9',
  '0.9-1.0',
];

export function bucketScores(results: Result[]): Bucket[] {
  const counts = new Array<number>(10).fill(0);

  for (const r of results) {
    if (r.score != null) {
      const index = Math.min(Math.floor(r.score * 10), 9);
      counts[index]!++;
    }
  }

  return BUCKET_LABELS.map((label, i) => ({
    label,
    count: counts[i]!,
  }));
}
