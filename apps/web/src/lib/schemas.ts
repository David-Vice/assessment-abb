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

export const CitationSchema = z.object({
  url: z.string(),
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
  url: z.string(),
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

export type Language = z.infer<typeof LanguageSchema>;
export type Segment = z.infer<typeof SegmentSchema>;
export type AnswerStatus = z.infer<typeof AnswerStatusSchema>;
export type IngestionState = z.infer<typeof IngestionStateSchema>;
export type Citation = z.infer<typeof CitationSchema>;
export type ChatResponse = z.infer<typeof ChatResponseSchema>;
export type IngestionJob = z.infer<typeof IngestionJobSchema>;
export type IngestionStatus = z.infer<typeof IngestionStatusSchema>;
export type CorpusDocument = z.infer<typeof CorpusDocumentSchema>;
export type Corpus = z.infer<typeof CorpusSchema>;
