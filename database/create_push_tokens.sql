-- Push token tablosu.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS push_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'fcm',
    cihaz_id TEXT,
    olusturulma_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT push_tokens_provider_valid CHECK (provider IN ('fcm', 'expo', 'apns')),
    CONSTRAINT push_tokens_length_valid CHECK (length(token) BETWEEN 20 AND 4096)
);

CREATE UNIQUE INDEX IF NOT EXISTS push_tokens_token_unique_idx ON push_tokens(token);
CREATE INDEX IF NOT EXISTS push_tokens_provider_idx ON push_tokens(provider);
