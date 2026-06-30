import localforage from 'localforage';

import { CorpusSchema } from './schemas';
import type { Corpus } from './schemas';

const store = localforage.createInstance({ name: 'abb-rag' });

export async function saveCorpus(corpus: Corpus): Promise<void> {
  await store.setItem('corpus', corpus);
}

export async function loadCorpus(): Promise<Corpus | null> {
  const raw = await store.getItem<unknown>('corpus');
  if (!raw) return null;
  const result = CorpusSchema.safeParse(raw);
  return result.success ? result.data : null;
}

export async function clearCorpus(): Promise<void> {
  await store.removeItem('corpus');
}
