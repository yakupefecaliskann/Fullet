-- Push token hardening.
-- Flutter icin FCM, eski sistem icin Expo, ileride iOS icin APNS desteklenir.

ALTER TABLE push_tokens
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'fcm',
  ADD COLUMN IF NOT EXISTS cihaz_id TEXT,
  ADD COLUMN IF NOT EXISTS son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'push_tokens_provider_valid'
  ) THEN
    ALTER TABLE push_tokens
      ADD CONSTRAINT push_tokens_provider_valid CHECK (provider IN ('fcm', 'expo', 'apns'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'push_tokens_length_valid'
  ) THEN
    ALTER TABLE push_tokens
      ADD CONSTRAINT push_tokens_length_valid CHECK (length(token) BETWEEN 20 AND 4096);
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS push_tokens_token_unique_idx ON push_tokens(token);
CREATE INDEX IF NOT EXISTS push_tokens_provider_idx ON push_tokens(provider);

ALTER TABLE push_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon insert push token" ON push_tokens;
CREATE POLICY "anon insert push token"
ON push_tokens FOR INSERT
TO anon, authenticated
WITH CHECK (
  length(token) BETWEEN 20 AND 4096
  AND provider IN ('fcm', 'expo', 'apns')
);
