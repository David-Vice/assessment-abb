import * as React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { TimeBucket } from '@/lib/schemas';
import { AXIS_COLOR, CHART_COLORS, ChartCard } from './chart-card';
import { fillBuckets } from '../lib/fill-buckets';

interface VolumeChartProps {
  points: TimeBucket[];
  granularity: 'hour' | 'day';
  from: string;
  to: string;
}

export function VolumeChart({
  points,
  granularity,
  from,
  to,
}: VolumeChartProps): React.JSX.Element {
  const { t } = useTranslation();

  const data = fillBuckets(points, from, to, granularity).map((p) => ({
    label: formatBucket(p.bucket, granularity),
    count: p.count,
  }));

  return (
    <ChartCard
      title={t('dashboard.charts.volume')}
      isEmpty={points.length === 0}
      emptyText={t('dashboard.empty')}
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS[0]} stopOpacity={0.4} />
              <stop offset="100%" stopColor={CHART_COLORS[0]} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={AXIS_COLOR} strokeOpacity={0.2} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: AXIS_COLOR }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: AXIS_COLOR }} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
            labelStyle={{ color: AXIS_COLOR }}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke={CHART_COLORS[0]}
            strokeWidth={2}
            fill="url(#volumeFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// Buckets come back from Postgres as UTC; use the UTC getters (not local-time
// ones) or labels shift by the browser's offset (e.g. ~4h for Baku/UTC+4).
function formatBucket(iso: string, granularity: 'hour' | 'day'): string {
  const date = new Date(iso);
  if (granularity === 'hour') {
    return `${date.getUTCHours()}:00`;
  }
  return `${date.getUTCMonth() + 1}/${date.getUTCDate()}`;
}
