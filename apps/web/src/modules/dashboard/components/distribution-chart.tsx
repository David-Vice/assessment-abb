import * as React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { DistributionStats } from '@/lib/schemas';
import { AXIS_COLOR, CHART_COLORS, ChartCard } from './chart-card';

interface DistributionChartProps {
  distribution?: DistributionStats;
}

export function DistributionChart({ distribution }: DistributionChartProps): React.JSX.Element {
  const { t } = useTranslation();

  const langData = Object.entries(distribution?.by_language ?? {}).map(([key, value]) => ({
    name: key.toUpperCase(),
    value,
  }));
  const segData = Object.entries(distribution?.by_segment ?? {}).map(([key, value]) => ({
    name: key,
    value,
  }));

  const isEmpty = langData.length === 0 && segData.length === 0;

  return (
    <ChartCard
      title={t('dashboard.charts.distribution')}
      isEmpty={isEmpty}
      emptyText={t('dashboard.empty')}
    >
      <div className="grid h-full grid-cols-2 gap-2">
        <MiniBars title={t('dashboard.byLanguage')} data={langData} />
        <MiniBars title={t('dashboard.bySegment')} data={segData} />
      </div>
    </ChartCard>
  );
}

interface MiniBarsProps {
  title: string;
  data: { name: string; value: number }[];
}

function MiniBars({ title, data }: MiniBarsProps): React.JSX.Element {
  return (
    <div className="flex h-full flex-col">
      <p className="mb-1 text-center text-[11px] font-medium text-muted-foreground">{title}</p>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: AXIS_COLOR }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: AXIS_COLOR }} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} cursor={{ opacity: 0.1 }} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
