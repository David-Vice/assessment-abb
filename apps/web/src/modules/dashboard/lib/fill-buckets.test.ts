import { describe, expect, it } from 'vitest';

import { fillBuckets } from './fill-buckets';

describe('fillBuckets', () => {
  it('fills missing hour buckets with zero counts', () => {
    const points = [{ bucket: '2026-01-01T00:00:00.000Z', count: 5 }];
    const filled = fillBuckets(points, '2026-01-01T00:00:00.000Z', '2026-01-01T02:00:00.000Z', 'hour');

    expect(filled).toEqual([
      { bucket: '2026-01-01T00:00:00.000Z', count: 5 },
      { bucket: '2026-01-01T01:00:00.000Z', count: 0 },
      { bucket: '2026-01-01T02:00:00.000Z', count: 0 },
    ]);
  });

  it('fills missing day buckets with zero counts', () => {
    const points = [{ bucket: '2026-01-03T00:00:00.000Z', count: 2 }];
    const filled = fillBuckets(points, '2026-01-01T00:00:00.000Z', '2026-01-03T00:00:00.000Z', 'day');

    expect(filled.map((p) => p.count)).toEqual([0, 0, 2]);
    expect(filled).toHaveLength(3);
  });

  it('matches buckets regardless of sub-bucket time offset', () => {
    const points = [{ bucket: '2026-01-01T05:42:17.000Z', count: 7 }];
    const filled = fillBuckets(points, '2026-01-01T00:00:00.000Z', '2026-01-01T10:00:00.000Z', 'hour');

    const hour5 = filled.find((p) => p.bucket === '2026-01-01T05:00:00.000Z');
    expect(hour5?.count).toBe(7);
  });

  it('returns the original points when the range is invalid', () => {
    const points = [{ bucket: '2026-01-01T00:00:00.000Z', count: 1 }];
    expect(fillBuckets(points, 'not-a-date', '2026-01-01T00:00:00.000Z', 'hour')).toBe(points);
  });
});
