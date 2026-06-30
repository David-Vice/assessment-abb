import { render, screen } from '@testing-library/react';

import '@/i18n/index';
import type { AnalyticsSummary, PerformanceStats } from '@/lib/schemas';
import { KpiCards } from './kpi-cards';

const summary: AnalyticsSummary = {
  total_questions: 42,
  answered_rate: 0.75,
  avg_latency_ms: 321,
};
const performance: PerformanceStats = {
  avg_latency_ms: 321,
  p95_latency_ms: 500,
  avg_total_tokens: 150,
  estimated_cost_usd: 1.23,
};

describe('KpiCards', () => {
  it('renders real values once data has loaded', () => {
    render(<KpiCards summary={summary} performance={performance} isLoading={false} />);

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('$1.23')).toBeInTheDocument();
  });

  it('shows pulse placeholders instead of fake zeros while loading', () => {
    render(<KpiCards summary={undefined} performance={undefined} isLoading />);

    expect(screen.queryByText('0')).not.toBeInTheDocument();
    expect(screen.queryByText('$0.00')).not.toBeInTheDocument();
    expect(document.querySelectorAll('.animate-pulse')).toHaveLength(6);
  });
});
