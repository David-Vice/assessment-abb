import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { Language } from '@/lib/schemas';

type CorpusStatus = 'none' | 'ingesting' | 'ready' | 'failed';

interface AppStore {
  language: Language;
  theme: 'light' | 'dark';
  corpusStatus: CorpusStatus;
  jobId: string | null;
  sessionId: string;
  docCount: number;
  ingestionError: string | null;

  setLanguage: (lang: Language) => void;
  toggleTheme: () => void;
  setCorpusStatus: (s: CorpusStatus) => void;
  setJobId: (id: string | null) => void;
  setDocCount: (n: number) => void;
  setIngestionError: (e: string | null) => void;
  resetSession: () => void;
  resetCorpus: () => void;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      language: 'en',
      theme: 'light',
      corpusStatus: 'none',
      jobId: null,
      sessionId: crypto.randomUUID(),
      docCount: 0,
      ingestionError: null,

      setLanguage: (language) => set({ language }),
      toggleTheme: () => set((s) => ({ theme: s.theme === 'light' ? 'dark' : 'light' })),
      setCorpusStatus: (corpusStatus) => set({ corpusStatus }),
      setJobId: (jobId) => set({ jobId }),
      setDocCount: (docCount) => set({ docCount }),
      setIngestionError: (ingestionError) => set({ ingestionError }),
      resetSession: () => set({ sessionId: crypto.randomUUID() }),
      resetCorpus: () => set({ corpusStatus: 'none', jobId: null, docCount: 0, ingestionError: null }),
    }),
    { name: 'abb-app' },
  ),
);
