import { ChatTurnSchema, IngestionJobSchema, IngestionStatusSchema } from './schemas';
import type { ChatTurn, Corpus, IngestionJob, IngestionStatus } from './schemas';

// In dev, use empty base so Vite proxy handles routing (no CORS).
// In production (Docker), Vite bakes in the VITE_* env vars at build time.
const DEV = import.meta.env.DEV;

export const CHAT_URL = DEV
  ? ''
  : ((import.meta.env.VITE_CHAT_URL as string | undefined) ?? 'http://localhost:8002');

export const INGESTION_URL = DEV
  ? ''
  : ((import.meta.env.VITE_INGESTION_URL as string | undefined) ?? 'http://localhost:8001');

export const ANALYTICS_URL = DEV
  ? ''
  : ((import.meta.env.VITE_ANALYTICS_URL as string | undefined) ?? 'http://localhost:8003');

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });

  if (!response.ok) {
    // Exclude raw body text: proxy error pages (HTML, nginx 503) would otherwise
    // leak into user-visible error messages.
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function postIngest(corpus: Corpus): Promise<IngestionJob> {
  const raw = await apiFetch<unknown>(`${INGESTION_URL}/ingest`, {
    method: 'POST',
    body: JSON.stringify({ corpus }),
  });
  return IngestionJobSchema.parse(raw);
}

export async function getIngestionStatus(jobId: string): Promise<IngestionStatus> {
  const raw = await apiFetch<unknown>(`${INGESTION_URL}/ingest/${jobId}`);
  return IngestionStatusSchema.parse(raw);
}

export async function getSession(sessionId: string): Promise<ChatTurn[]> {
  const raw = await apiFetch<unknown>(`${CHAT_URL}/sessions/${sessionId}`);
  return ChatTurnSchema.array().parse(raw);
}

export async function apiFetchAnalytics<T>(path: string): Promise<T> {
  return apiFetch<T>(`${ANALYTICS_URL}${path}`);
}
