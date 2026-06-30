import {
  AnalyticsSummarySchema,
  ChatTurnSchema,
  DistributionStatsSchema,
  IngestionJobSchema,
  IngestionStatusSchema,
  PerformanceStatsSchema,
  QualityStatsSchema,
  TopQuestionSchema,
  VolumeSeriesSchema,
} from './schemas';
import type {
  AnalyticsSummary,
  ChatTurn,
  Corpus,
  DistributionStats,
  IngestionJob,
  IngestionStatus,
  Language,
  PerformanceStats,
  QualityStats,
  TopQuestion,
  VolumeSeries,
} from './schemas';

export interface AnalyticsFilters {
  from?: string;
  to?: string;
  lang?: Language;
}

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

function analyticsQuery(filters: AnalyticsFilters, extra?: Record<string, string>): string {
  const params = new URLSearchParams();
  if (filters.from) params.set('from', filters.from);
  if (filters.to) params.set('to', filters.to);
  if (filters.lang) params.set('lang', filters.lang);
  for (const [key, value] of Object.entries(extra ?? {})) params.set(key, value);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function getAnalyticsSummary(filters: AnalyticsFilters): Promise<AnalyticsSummary> {
  const raw = await apiFetch<unknown>(`${ANALYTICS_URL}/analytics/summary${analyticsQuery(filters)}`);
  return AnalyticsSummarySchema.parse(raw);
}

export async function getAnalyticsVolume(
  filters: AnalyticsFilters,
  bucket: 'hour' | 'day',
): Promise<VolumeSeries> {
  const path = `/analytics/volume${analyticsQuery(filters, { bucket })}`;
  const raw = await apiFetch<unknown>(`${ANALYTICS_URL}${path}`);
  return VolumeSeriesSchema.parse(raw);
}

export async function getAnalyticsTopQuestions(filters: AnalyticsFilters): Promise<TopQuestion[]> {
  const path = `/analytics/top-questions${analyticsQuery(filters)}`;
  const raw = await apiFetch<unknown>(`${ANALYTICS_URL}${path}`);
  return TopQuestionSchema.array().parse(raw);
}

export async function getAnalyticsPerformance(
  filters: AnalyticsFilters,
): Promise<PerformanceStats> {
  const path = `/analytics/performance${analyticsQuery(filters)}`;
  const raw = await apiFetch<unknown>(`${ANALYTICS_URL}${path}`);
  return PerformanceStatsSchema.parse(raw);
}

export async function getAnalyticsQuality(filters: AnalyticsFilters): Promise<QualityStats> {
  const raw = await apiFetch<unknown>(`${ANALYTICS_URL}/analytics/quality${analyticsQuery(filters)}`);
  return QualityStatsSchema.parse(raw);
}

export async function getAnalyticsDistribution(
  filters: AnalyticsFilters,
): Promise<DistributionStats> {
  const path = `/analytics/distribution${analyticsQuery(filters)}`;
  const raw = await apiFetch<unknown>(`${ANALYTICS_URL}${path}`);
  return DistributionStatsSchema.parse(raw);
}
