import { CheckCircle, XCircle } from 'lucide-react';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Progress } from '@/components/ui/progress';
import type { IngestionStatus } from '@/lib/schemas';

interface IngestionProgressProps {
  status: IngestionStatus | undefined;
}

export function IngestionProgress({ status }: IngestionProgressProps): React.JSX.Element {
  const { t } = useTranslation();

  const percent =
    status && status.total > 0 ? Math.round((status.processed / status.total) * 100) : 0;

  const isFailed = status?.state === 'failed';
  const isCompleted = status?.state === 'completed';

  return (
    <div className="flex flex-col items-center gap-6">
      {isCompleted ? (
        <CheckCircle className="h-14 w-14 text-green-500" strokeWidth={1.5} />
      ) : isFailed ? (
        <XCircle className="h-14 w-14 text-destructive" strokeWidth={1.5} />
      ) : (
        <div className="relative h-14 w-14">
          <svg className="animate-spin h-14 w-14 text-primary" viewBox="0 0 56 56" fill="none">
            <circle
              cx="28"
              cy="28"
              r="24"
              stroke="currentColor"
              strokeWidth="4"
              strokeOpacity="0.2"
            />
            <path
              d="M28 4a24 24 0 0 1 24 24"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
            />
          </svg>
        </div>
      )}

      <div className="w-full text-center space-y-2">
        {isCompleted && (
          <p className="text-sm font-semibold text-green-600 dark:text-green-400">
            {t('upload.ready')}
          </p>
        )}
        {isFailed && (
          <>
            <p className="text-sm font-semibold text-destructive">{t('upload.failed')}</p>
            {status?.error && (
              <p className="text-xs text-muted-foreground">{t('upload.errorDetail', { message: status.error })}</p>
            )}
          </>
        )}
        {!isCompleted && !isFailed && (
          <>
            <p className="text-sm font-medium text-muted-foreground">{t('upload.indexing')}</p>
            {status && status.total > 0 && (
              <p className="text-xs text-muted-foreground">
                {t('upload.progress', { processed: status.processed, total: status.total })}
              </p>
            )}
            <Progress value={percent} className="mt-2" />
          </>
        )}
      </div>
    </div>
  );
}
