import localforage from 'localforage';

import type { Corpus } from './schemas';

const store = localforage.createInstance({ name: 'abb-rag' });

export async function saveCorpus(corpus: Corpus): Promise<void> {
  await store.setItem('corpus', corpus);
}
