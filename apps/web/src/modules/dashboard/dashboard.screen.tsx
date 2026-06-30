import { MessageSquare } from 'lucide-react';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Header } from '@/modules/common/components/header';

import { ChartCard } from './components/chart-card';
import { DateRangeFilter } from './components/date-range-filter';
import { DistributionChart } from './components/distribution-chart';
import { KpiCards } from './components/kpi-cards';
import { QualityChart } from './components/quality-chart';
import { TopQuestionsChart } from './components/top-questions-chart';
import { VolumeChart } from './components/volume-chart';
import { useAnalytics } from './hooks/use-analytics';

interface DashboardScreenProps {
  onGoToChat: () => void;
}

export function DashboardScreen({ onGoToChat }: DashboardScreenProps): React.JSX.Element {
  const { t } = useTranslation();
  const {
    preset,
    setPreset,
    lang,
    setLang,
    summary,
    performance,
    volume,
    quality,
    distribution,
    topQuestions,
  } = useAnalytics();

  const granularity = preset === '24h' ? 'hour' : 'day';
  const hasError =
    summary.isError ||
    volume.isError ||
    quality.isError ||
    distribution.isError ||
    topQuestions.isError;

  const headerActions = (
    <Button variant="ghost" size="sm" onClick={onGoToChat} className="gap-1.5 text-xs">
      <MessageSquare className="h-3.5 w-3.5" />
      {t('nav.chat')}
    </Button>
  );

  return (
    <div className="flex h-screen flex-col">
      <Header actions={headerActions} />

      <main className="flex-1 overflow-y-auto scrollbar-thin bg-background p-4 sm:p-6">
        <div className="mx-auto max-w-6xl space-y-5">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight">{t('dashboard.title')}</h1>
            <p className="text-sm text-muted-foreground">{t('dashboard.subtitle')}</p>
          </div>

          <DateRangeFilter
            preset={preset}
            onPresetChange={setPreset}
            lang={lang}
            onLangChange={setLang}
          />

          {hasError ? (
            <ChartCard title={t('dashboard.title')} isEmpty emptyText={t('dashboard.error')}>
              <span />
            </ChartCard>
          ) : (
            <>
              <KpiCards summary={summary.data} performance={performance.data} />

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <VolumeChart points={volume.data?.points ?? []} granularity={granularity} />
                <QualityChart quality={quality.data} />
                <DistributionChart distribution={distribution.data} />
                <TopQuestionsChart questions={topQuestions.data ?? []} />
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
