import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Card, CardContent } from '@/components/ui/card';
import type { AnalyticsSummary, PerformanceStats } from '@/lib/schemas';

interface KpiCardsProps {
  summary?: AnalyticsSummary;
  performance?: PerformanceStats;
}

interface Kpi {
  label: string;
  value: string;
}

export function KpiCards({ summary, performance }: KpiCardsProps): React.JSX.Element {
  const { t } = useTranslation();

  const kpis: Kpi[] = [
    { label: t('dashboard.kpi.totalQuestions'), value: (summary?.total_questions ?? 0).toString() },
    {
      label: t('dashboard.kpi.answeredRate'),
      value: `${Math.round((summary?.answered_rate ?? 0) * 100)}%`,
    },
    {
      label: t('dashboard.kpi.avgLatency'),
      value: `${Math.round(summary?.avg_latency_ms ?? 0)} ms`,
    },
    {
      label: t('dashboard.kpi.p95Latency'),
      value: `${Math.round(performance?.p95_latency_ms ?? 0)} ms`,
    },
    {
      label: t('dashboard.kpi.avgTokens'),
      value: Math.round(performance?.avg_total_tokens ?? 0).toString(),
    },
    {
      label: t('dashboard.kpi.estCost'),
      value: `$${(performance?.estimated_cost_usd ?? 0).toFixed(2)}`,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {kpis.map((kpi) => (
        <Card key={kpi.label}>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold tracking-tight">{kpi.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
