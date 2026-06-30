import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Header } from '@/modules/common/components/header';
import { useAppStore } from '@/store/app-store';

import { Dropzone } from './components/dropzone';
import { IngestionProgress } from './components/ingestion-progress';
import { useCorpus } from './hooks/use-corpus';
import { useIngestion } from './hooks/use-ingestion';

export function UploadScreen(): React.JSX.Element {
  const { t } = useTranslation();
  const corpusStatus = useAppStore((s) => s.corpusStatus);
  const docCount = useAppStore((s) => s.docCount);

  const { processFile, uploadState, corpus, error, reset } = useCorpus();
  const { start, status, isStarting, startError } = useIngestion();

  const handleFile = async (file: File) => {
    const parsed = await processFile(file);
    if (parsed) {
      start(parsed);
    }
  };

  const isIngesting = corpusStatus === 'ingesting';

  return (
    <div className="flex flex-col h-screen">
      <Header />

      <main className="flex-1 flex items-center justify-center p-6 bg-background">
        <div className="w-full max-w-lg space-y-6">
          {/* Hero text */}
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold tracking-tight">{t('upload.title')}</h1>
            <p className="text-muted-foreground text-sm">{t('upload.subtitle')}</p>
          </div>

          <Card>
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
              {isIngesting ? (
                <IngestionProgress status={status} />
              ) : (
                <Dropzone
                  onFile={handleFile}
                  uploadState={uploadState}
                  error={error ?? startError}
                  docCount={corpus?.documents.length}
                />
              )}

              {/* Error from mutation */}
              {startError && !isIngesting && (
                <p className="mt-3 text-xs text-destructive text-center">{startError}</p>
              )}

              {/* Loading indicator on ingest start */}
              {isStarting && (
                <p className="mt-3 text-xs text-muted-foreground text-center animate-pulse">
                  {t('upload.uploading')}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Re-upload when already ready */}
          {corpusStatus === 'ready' && (
            <div className="text-center space-y-3">
              <p className="text-sm text-muted-foreground">{t('upload.alreadyReady')}</p>
              <p className="text-xs text-muted-foreground">
                {t('upload.documents', { count: docCount })}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={reset}
              >
                {t('upload.reUpload')}
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
