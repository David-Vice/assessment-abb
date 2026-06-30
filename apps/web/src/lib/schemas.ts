import { z } from 'zod';

export const LanguageSchema = z.enum(['az', 'en', 'ru']);
export const SegmentSchema = z.enum(['individuals', 'business', 'about', 'other']);
export const AnswerStatusSchema = z.enum([
  'answered',
  'declined_off_topic',
  'declined_injection',
  'error',
]);
export const IngestionStateSchema = z.enum(['queued', 'running', 'completed', 'failed']);

// Mirrors the backend Pydantic Citation.url = Field(pattern=r"^https?://").
const HTTP_URL = z.string().regex(/^https?:\/\//);

export const CitationSchema = z.object({
  url: HTTP_URL,
  title: z.string().nullable().optional(),
  language: LanguageSchema,
  segment: SegmentSchema.default('other'),
  snippet: z.string().nullable().optional(),
});

export const ChatResponseSchema = z.object({
  chat_log_id: z.number(),
  answer: z.string(),
  status: AnswerStatusSchema,
  citations: z.array(CitationSchema).default([]),
});

// Mirrors the backend ChatTurn contract (used for session hydration).
export const ChatTurnSchema = z.object({
  id: z.number(),
  session_id: z.string(),
  question: z.string(),
  answer: z.string(),
  language: LanguageSchema.nullable().optional(),
  status: AnswerStatusSchema,
  citations: z.array(CitationSchema).default([]),
  created_at: z.string(),
});

export const IngestionJobSchema = z.object({
  job_id: z.string(),
  state: IngestionStateSchema.default('queued'),
});

export const IngestionStatusSchema = z.object({
  job_id: z.string(),
  state: IngestionStateSchema,
  processed: z.number().default(0),
  total: z.number().default(0),
  error: z.string().nullable().optional(),
});

export const CorpusDocumentSchema = z.object({
  url: HTTP_URL,
  language: LanguageSchema,
  segment: SegmentSchema.default('other'),
  title: z.string().nullable().optional(),
  markdown: z.string(),
  content_hash: z.string(),
  fetched_at: z.string(),
});

export const CorpusSchema = z.object({
  version: z.number().default(1),
  source: z.string(),
  generated_at: z.string(),
  documents: z.array(CorpusDocumentSchema).default([]),
});

// --- Analytics (P6) — mirror packages/contracts/abb_contracts/analytics.py ---

export const TimeBucketSchema = z.object({
  bucket: z.string(),
  count: z.number(),
});

export const VolumeSeriesSchema = z.object({
  points: z.array(TimeBucketSchema).default([]),
});

export const TopQuestionSchema = z.object({
  question: z.string(),
  count: z.number(),
});

export const PerformanceStatsSchema = z.object({
  avg_latency_ms: z.number(),
  p95_latency_ms: z.number(),
  avg_total_tokens: z.number(),
  estimated_cost_usd: z.number(),
});

export const QualityStatsSchema = z.object({
  answered: z.number(),
  declined_off_topic: z.number(),
  declined_injection: z.number(),
  error: z.number(),
});

// String-keyed (not enum-keyed) because the backend only emits the languages /
// segments actually present; an enum-keyed record would demand every key.
export const DistributionStatsSchema = z.object({
  by_language: z.record(z.string(), z.number()).default({}),
  by_segment: z.record(z.string(), z.number()).default({}),
});

export const AnalyticsSummarySchema = z.object({
  total_questions: z.number(),
  answered_rate: z.number(),
  avg_latency_ms: z.number(),
});

export type TimeBucket = z.infer<typeof TimeBucketSchema>;
export type VolumeSeries = z.infer<typeof VolumeSeriesSchema>;
export type TopQuestion = z.infer<typeof TopQuestionSchema>;
export type PerformanceStats = z.infer<typeof PerformanceStatsSchema>;
export type QualityStats = z.infer<typeof QualityStatsSchema>;
export type DistributionStats = z.infer<typeof DistributionStatsSchema>;
export type AnalyticsSummary = z.infer<typeof AnalyticsSummarySchema>;

export type Language = z.infer<typeof LanguageSchema>;
export type Segment = z.infer<typeof SegmentSchema>;
export type AnswerStatus = z.infer<typeof AnswerStatusSchema>;
export type IngestionState = z.infer<typeof IngestionStateSchema>;
export type Citation = z.infer<typeof CitationSchema>;
export type ChatResponse = z.infer<typeof ChatResponseSchema>;
export type ChatTurn = z.infer<typeof ChatTurnSchema>;
export type IngestionJob = z.infer<typeof IngestionJobSchema>;
export type IngestionStatus = z.infer<typeof IngestionStatusSchema>;
export type CorpusDocument = z.infer<typeof CorpusDocumentSchema>;
export type Corpus = z.infer<typeof CorpusSchema>;
