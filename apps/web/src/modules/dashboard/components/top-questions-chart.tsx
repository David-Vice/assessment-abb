import * as React from 'react';
import { useTranslation } from 'react-i18next';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { TopQuestion } from '@/lib/schemas';
import { AXIS_COLOR, CHART_COLORS, ChartCard } from './chart-card';

interface TopQuestionsChartProps {
  questions: TopQuestion[];
}

const MAX_LABEL = 40;

export function TopQuestionsChart({ questions }: TopQuestionsChartProps): React.JSX.Element {
  const { t } = useTranslation();

  const data = questions.map((q) => ({
    label: q.question.length > MAX_LABEL ? `${q.question.slice(0, MAX_LABEL)}…` : q.question,
    count: q.count,
  }));

  return (
    <ChartCard
      title={t('dashboard.charts.topQuestions')}
      isEmpty={data.length === 0}
      emptyText={t('dashboard.empty')}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 12, bottom: 4, left: 8 }}
        >
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: AXIS_COLOR }} />
          <YAxis
            type="category"
            dataKey="label"
            width={180}
            tick={{ fontSize: 11, fill: AXIS_COLOR }}
          />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} cursor={{ opacity: 0.1 }} />
          <Bar dataKey="count" fill={CHART_COLORS[0]} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
