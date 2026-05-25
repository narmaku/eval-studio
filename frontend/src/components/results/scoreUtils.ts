import type { Score } from '@/types';

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

export function bucketScores(scores: Score[]): Bucket[] {
  const counts = new Array<number>(10).fill(0);

  for (const score of scores) {
    const index = Math.min(Math.floor(score.overall * 10), 9);
    counts[index]!++;
  }

  return BUCKET_LABELS.map((label, i) => ({
    label,
    count: counts[i]!,
  }));
}
