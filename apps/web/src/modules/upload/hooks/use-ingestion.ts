import { useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { getIngestionStatus, postIngest } from '@/lib/api';
import { useAppStore } from '@/store/app-store';
import type { Corpus, IngestionStatus } from '@/lib/schemas';

export interface UseIngestionResult {
  start: (corpus: Corpus) => void;
  status: IngestionStatus | undefined;
  isStarting: boolean;
  startError: string | null;
}

export function useIngestion(): UseIngestionResult {
  const jobId = useAppStore((s) => s.jobId);
  const setJobId = useAppStore((s) => s.setJobId);
  const setCorpusStatus = useAppStore((s) => s.setCorpusStatus);
  const setDocCount = useAppStore((s) => s.setDocCount);
  const setIngestionError = useAppStore((s) => s.setIngestionError);

  const mutation = useMutation({
    mutationFn: postIngest,
    onSuccess: (job) => {
      setJobId(job.job_id);
      setCorpusStatus('ingesting');
    },
  });

  const poll = useQuery({
    queryKey: ['ingestion', jobId],
    queryFn: () => getIngestionStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === 'completed' || state === 'failed' ? false : 2000;
    },
  });

  useEffect(() => {
    const state = poll.data?.state;
    if (state === 'completed') {
      setDocCount(poll.data?.total ?? 0);
      setCorpusStatus('ready');
      setJobId(null);
    } else if (state === 'failed') {
      setCorpusStatus('failed');
      setIngestionError(poll.data?.error ?? 'upload.failed');
      setJobId(null);
    }
  }, [poll.data?.state, poll.data?.total, setCorpusStatus, setDocCount, setJobId]);

  return {
    start: (corpus) => mutation.mutate(corpus),
    status: poll.data,
    isStarting: mutation.isPending,
    startError: mutation.error instanceof Error ? mutation.error.message : null,
  };
}
