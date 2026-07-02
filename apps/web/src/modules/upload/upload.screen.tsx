import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AbbLogo } from '@/modules/common/components/abb-logo';
import { Header } from '@/modules/common/components/header';
import { useAppStore } from '@/store/app-store';

import { Dropzone } from './components/dropzone';
import { IngestionProgress } from './components/ingestion-progress';
import { useCorpus } from './hooks/use-corpus';
import { useIngestion } from './hooks/use-ingestion';

interface UploadScreenProps {
  onLogoClick?: () => void;
}

export function UploadScreen({ onLogoClick }: UploadScreenProps): React.JSX.Element {
  const { t } = useTranslation();
  const corpusStatus = useAppStore((s) => s.corpusStatus);
  const jobId = useAppStore((s) => s.jobId);
  const ingestionError = useAppStore((s) => s.ingestionError);
  const resetCorpus = useAppStore((s) => s.resetCorpus);

  const { processFile, uploadState, corpus, error, reset } = useCorpus();
  const { start, status, isStarting, startError } = useIngestion();

  const handleFile = async (file: File) => {
    const parsed = await processFile(file);
    if (parsed) {
      start(parsed);
    }
  };

  const handleRetry = () => {
    resetCorpus();
    reset();
  };

  const isIngesting = corpusStatus === 'ingesting' || (!!jobId && corpusStatus === 'ready');
  const isFailed = corpusStatus === 'failed';

  return (
    <div className="abb-app-shell abb-page-bg">
      <Header onLogoClick={onLogoClick} />

      <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden p-3 sm:flex sm:items-center sm:justify-center sm:p-6">
        <div className="mx-auto w-full max-w-lg space-y-5 sm:space-y-6">
          <div className="space-y-2 text-center">
            <div className="flex justify-center sm:hidden">
              <AbbLogo height={36} />
            </div>
            <h1 className="text-xl font-bold tracking-tight sm:text-3xl">
              <span className="abb-gradient-text">{t('upload.title')}</span>
            </h1>
            <p className="text-sm leading-relaxed text-muted-foreground">{t('upload.subtitle')}</p>
          </div>

          <Card className="border-border/80 shadow-soft">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {isIngesting ? t('upload.indexing') : t('upload.dropHere')}
              </CardTitle>
              {isIngesting && status?.total ? (
                <CardDescription>
                  {t('upload.documents', { count: status.total })}
                </CardDescription>
              ) : null}
            </CardHeader>

            <CardContent>
              {isFailed ? (
                <div className="flex flex-col items-center gap-4 py-6 text-center">
                  <p className="text-sm text-destructive">
                    {t(ingestionError ?? 'upload.failed', { defaultValue: ingestionError ?? t('upload.failed') })}
                  </p>
                  <Button variant="outline" size="sm" onClick={handleRetry}>
                    {t('upload.tryAgain')}
                  </Button>
                </div>
              ) : isIngesting ? (
                <IngestionProgress status={status} />
              ) : (
                <Dropzone
                  onFile={handleFile}
                  uploadState={uploadState}
                  error={error ?? startError}
                  docCount={corpus?.documents.length}
                />
              )}

              {/* Error from mutation (e.g. network failure before job is queued) */}
              {startError && !isIngesting && !isFailed && (
                <p className="mt-3 text-xs text-destructive text-center">{startError}</p>
              )}

              {isStarting && (
                <p className="mt-3 text-xs text-muted-foreground text-center animate-pulse">
                  {t('upload.uploading')}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
