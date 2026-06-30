import * as React from 'react';
import { useTranslation } from 'react-i18next';
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

import type { QualityStats } from '@/lib/schemas';
import { CHART_COLORS, ChartCard } from './chart-card';

interface QualityChartProps {
  quality?: QualityStats;
}

export function QualityChart({ quality }: QualityChartProps): React.JSX.Element {
  const { t } = useTranslation();

  const data = [
    { name: t('dashboard.quality.answered'), value: quality?.answered ?? 0, color: CHART_COLORS[2] },
    {
      name: t('dashboard.quality.offTopic'),
      value: quality?.declined_off_topic ?? 0,
      color: CHART_COLORS[3],
    },
    {
      name: t('dashboard.quality.injection'),
      value: quality?.declined_injection ?? 0,
      color: CHART_COLORS[4],
    },
    { name: t('dashboard.quality.error'), value: quality?.error ?? 0, color: CHART_COLORS[5] },
  ].filter((d) => d.value > 0);

  return (
    <ChartCard
      title={t('dashboard.charts.quality')}
      isEmpty={data.length === 0}
      emptyText={t('dashboard.empty')}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
