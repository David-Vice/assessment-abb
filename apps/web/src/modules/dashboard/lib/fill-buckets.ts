import type { TimeBucket } from '@/lib/schemas';

const HOUR_MS = 60 * 60 * 1000;
const DAY_MS = 24 * HOUR_MS;

/** Truncate to the start of the UTC hour or day — must match Postgres `date_trunc`. */
function truncateUtc(date: Date, granularity: 'hour' | 'day'): Date {
  const truncated = new Date(date);
  truncated.setUTCMinutes(0, 0, 0);
  if (granularity === 'day') {
    truncated.setUTCHours(0);
  }
  return truncated;
}

/**
 * Fill gaps between `from` and `to` with zero-count buckets.
 *
 * The backend only returns rows for buckets that have data (`GROUP BY` omits
 * empty ones), so a sparse range renders as a misleading straight line across
 * gaps in an AreaChart. This inserts explicit `count: 0` points for every
 * missing bucket at the chosen granularity.
 */
export function fillBuckets(
  points: TimeBucket[],
  from: string,
  to: string,
  granularity: 'hour' | 'day',
): TimeBucket[] {
  const stepMs = granularity === 'hour' ? HOUR_MS : DAY_MS;
  const start = truncateUtc(new Date(from), granularity).getTime();
  const end = new Date(to).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || start > end) {
    return points;
  }

  const countByBucket = new Map(
    points.map((point) => [truncateUtc(new Date(point.bucket), granularity).getTime(), point.count]),
  );

  const filled: TimeBucket[] = [];
  for (let t = start; t <= end; t += stepMs) {
    filled.push({ bucket: new Date(t).toISOString(), count: countByBucket.get(t) ?? 0 });
  }
  return filled;
}
