import { FileJson, UploadCloud } from 'lucide-react';
import * as React from 'react';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { UploadState } from '../hooks/use-corpus';

interface DropzoneProps {
  onFile: (file: File) => void;
  uploadState: UploadState;
  error: string | null;
  docCount?: number;
}

export function Dropzone({
  onFile,
  uploadState,
  error,
  docCount,
}: DropzoneProps): React.JSX.Element {
  const { t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (file.name.endsWith('.json')) {
        onFile(file);
      }
    },
    [onFile],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const isLoading = uploadState === 'validating';
  const isValid = uploadState === 'valid';
  const isInvalid = uploadState === 'invalid';

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      className={cn(
        'flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-10 transition-colors cursor-pointer',
        isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-accent/30',
        isValid && 'border-green-500 bg-green-50 dark:bg-green-950/20',
        isInvalid && 'border-destructive bg-destructive/5',
      )}
      onClick={() => !isLoading && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      aria-label="Upload corpus file"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={onInputChange}
      />

      {isValid ? (
        <FileJson className="h-12 w-12 text-green-500" strokeWidth={1.5} />
      ) : (
        <UploadCloud
          className={cn('h-12 w-12', isDragging ? 'text-primary' : 'text-muted-foreground')}
          strokeWidth={1.5}
        />
      )}

      <div className="text-center">
        {isLoading && (
          <p className="text-sm text-muted-foreground animate-pulse">{t('upload.validating')}</p>
        )}
        {isValid && (
          <>
            <p className="text-sm font-medium text-green-600 dark:text-green-400">
              {t('upload.uploading')}
            </p>
            {docCount !== undefined && (
              <p className="text-xs text-muted-foreground mt-1">
                {t('upload.documents', { count: docCount })}
              </p>
            )}
          </>
        )}
        {!isLoading && !isValid && (
          <>
            <p className="text-sm font-medium">{t('upload.dropHere')}</p>
            <p className="text-xs text-muted-foreground mt-1">{t('upload.orClick')}</p>
          </>
        )}
      </div>

      {isInvalid && error && (
        <p className="text-xs text-destructive text-center max-w-xs">{error}</p>
      )}

      {isInvalid && (
        <Button
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            inputRef.current?.click();
          }}
        >
          {t('upload.tryAgain')}
        </Button>
      )}
    </div>
  );
}
