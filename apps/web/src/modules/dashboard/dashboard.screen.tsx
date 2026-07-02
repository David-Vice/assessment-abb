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
  onLogoClick?: () => void;
}

export function DashboardScreen({ onGoToChat, onLogoClick }: DashboardScreenProps): React.JSX.Element {
  const { t } = useTranslation();
  const {
    preset,
    setPreset,
    lang,
    setLang,
    from,
    to,
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
    performance.isError ||
    volume.isError ||
    quality.isError ||
    distribution.isError ||
    topQuestions.isError;
  const kpisLoading = summary.isPending || performance.isPending;

  const headerActions = (
    <Button
      variant="ghost"
      size="icon"
      onClick={onGoToChat}
      className="h-10 w-10 shrink-0 sm:h-8 sm:w-auto sm:px-3"
      aria-label={t('nav.chat')}
    >
      <MessageSquare className="h-4 w-4" />
      <span className="hidden sm:inline sm:ml-1.5 sm:text-xs">{t('nav.chat')}</span>
    </Button>
  );

  return (
    <div className="abb-app-shell abb-page-bg">
      <Header actions={headerActions} onLogoClick={onLogoClick} />

      <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin p-3 sm:p-6">
        <div className="mx-auto max-w-6xl space-y-4 sm:space-y-5">
          <div className="space-y-1">
            <h1 className="text-xl font-bold tracking-tight sm:text-2xl">{t('dashboard.title')}</h1>
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
              <KpiCards
                summary={summary.data}
                performance={performance.data}
                isLoading={kpisLoading}
              />

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <VolumeChart
                  points={volume.data?.points ?? []}
                  granularity={granularity}
                  from={from}
                  to={to}
                />
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
