-- Extensions: vector search + accent-insensitive / fuzzy multilingual full-text.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent() is STABLE, but generated columns require IMMUTABLE expressions.
-- Pin the dictionary explicitly so this wrapper is genuinely deterministic.
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
    RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    AS $$ SELECT unaccent('unaccent', $1) $$;

CREATE TABLE IF NOT EXISTS documents (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    url           TEXT NOT NULL UNIQUE,
    language      TEXT NOT NULL CHECK (language IN ('az', 'en', 'ru')),
    segment       TEXT CHECK (segment IN ('individuals', 'business', 'about', 'other')),
    title         TEXT,
    content_hash  TEXT NOT NULL,
    fetched_at    TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id   BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal       INT NOT NULL,
    content       TEXT NOT NULL,
    language      TEXT NOT NULL CHECK (language IN ('az', 'en', 'ru')),
    segment       TEXT CHECK (segment IN ('individuals', 'business', 'about', 'other')),
    -- halfvec (not vector): pgvector's HNSW/IVFFlat cap `vector` indexes at 2000
    -- dims; text-embedding-3-large is 3072. halfvec indexes up to 4000 dims at
    -- half the storage with negligible recall loss.
    embedding     HALFVEC(3072),
    -- Uniform 'simple' + unaccent config so AZ/RU/EN are treated equally
    -- (Postgres has no Azerbaijani stemmer; no language is privileged).
    tsv           TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', immutable_unaccent(content))) STORED,
    token_count   INT,
    UNIQUE (document_id, ordinal)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding halfvec_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin        ON chunks USING gin (tsv);
-- Index the SAME expression the sparse query filters on (immutable_unaccent),
-- so the `<%` word-similarity operator can actually use this trigram index.
CREATE INDEX IF NOT EXISTS chunks_content_trgm   ON chunks USING gin (immutable_unaccent(content) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS chunks_lang_idx       ON chunks (language);

CREATE TABLE IF NOT EXISTS chat_logs (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id        UUID NOT NULL,
    question          TEXT NOT NULL,
    answer            TEXT NOT NULL,
    language          TEXT CHECK (language IN ('az', 'en', 'ru')),
    status            TEXT NOT NULL DEFAULT 'answered'
                          CHECK (status IN ('answered', 'declined_off_topic',
                                            'declined_injection', 'error')),
    citations         JSONB NOT NULL DEFAULT '[]',
    retrieved_ids     BIGINT[] NOT NULL DEFAULT '{}',
    model             TEXT,
    prompt_tokens     INT,
    completion_tokens INT,
    latency_ms        INT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_logs_session_idx ON chat_logs (session_id);
CREATE INDEX IF NOT EXISTS chat_logs_created_idx ON chat_logs (created_at);
