import { useCallback, useState } from 'react';

import { saveCorpus } from '@/lib/lf';
import { CorpusSchema } from '@/lib/schemas';
import type { Corpus } from '@/lib/schemas';

export type UploadState = 'idle' | 'validating' | 'valid' | 'invalid';

export interface UseCorpusResult {
  uploadState: UploadState;
  corpus: Corpus | null;
  error: string | null;
  processFile: (file: File) => Promise<Corpus | null>;
  reset: () => void;
}

export function useCorpus(): UseCorpusResult {
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [corpus, setCorpus] = useState<Corpus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const processFile = useCallback(async (file: File): Promise<Corpus | null> => {
    setUploadState('validating');
    setError(null);
    setCorpus(null);

    try {
      const text = await file.text();
      const json = JSON.parse(text) as unknown;
      const result = CorpusSchema.safeParse(json);

      if (!result.success) {
        const msg = result.error.issues[0]?.message ?? 'Unknown validation error';
        setError(msg);
        setUploadState('invalid');
        return null;
      }

      await saveCorpus(result.data);
      setCorpus(result.data);
      setUploadState('valid');
      return result.data;
    } catch {
      setError('Failed to parse JSON — ensure the file is a valid corpus.json');
      setUploadState('invalid');
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setUploadState('idle');
    setCorpus(null);
    setError(null);
  }, []);

  return { uploadState, corpus, error, processFile, reset };
}
