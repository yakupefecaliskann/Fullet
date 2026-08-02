-- Fullet admin/observability schema.
-- Run this in Supabase SQL Editor before enabling the web admin panel.
-- After running it, add your admin email:
-- INSERT INTO public.admin_emails (email) VALUES ('your-email@example.com') ON CONFLICT DO NOTHING;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.admin_emails (
  email TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.admin_emails ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON public.admin_emails TO authenticated;

CREATE OR REPLACE FUNCTION public.is_fullet_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.admin_emails
    WHERE LOWER(email) = LOWER(auth.email())
  );
$$;

REVOKE ALL ON FUNCTION public.is_fullet_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_fullet_admin() TO authenticated;

DROP POLICY IF EXISTS "admins read admin emails" ON public.admin_emails;
CREATE POLICY "admins read admin emails"
ON public.admin_emails
FOR SELECT
TO authenticated
USING (public.is_fullet_admin());

CREATE TABLE IF NOT EXISTS public.app_heartbeats (
  install_id UUID PRIMARY KEY,
  first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  app_version TEXT,
  platform TEXT,
  heartbeat_count INTEGER NOT NULL DEFAULT 1,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE public.app_heartbeats ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON public.app_heartbeats TO authenticated;

DROP POLICY IF EXISTS "admins read app heartbeats" ON public.app_heartbeats;
CREATE POLICY "admins read app heartbeats"
ON public.app_heartbeats
FOR SELECT
TO authenticated
USING (public.is_fullet_admin());

CREATE OR REPLACE FUNCTION public.record_app_heartbeat(
  p_install_id UUID,
  p_app_version TEXT DEFAULT NULL,
  p_platform TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.app_heartbeats (
    install_id,
    first_seen,
    last_seen,
    app_version,
    platform,
    heartbeat_count
  )
  VALUES (
    p_install_id,
    NOW(),
    NOW(),
    NULLIF(LEFT(COALESCE(p_app_version, ''), 64), ''),
    NULLIF(LEFT(COALESCE(p_platform, ''), 32), ''),
    1
  )
  ON CONFLICT (install_id)
  DO UPDATE SET
    last_seen = NOW(),
    app_version = COALESCE(EXCLUDED.app_version, public.app_heartbeats.app_version),
    platform = COALESCE(EXCLUDED.platform, public.app_heartbeats.platform),
    heartbeat_count = public.app_heartbeats.heartbeat_count + 1;
END;
$$;

REVOKE ALL ON FUNCTION public.record_app_heartbeat(UUID, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.record_app_heartbeat(UUID, TEXT, TEXT) TO anon, authenticated;

CREATE TABLE IF NOT EXISTS public.bot_runs (
  id BIGSERIAL PRIMARY KEY,
  bot_name TEXT NOT NULL,
  run_mode TEXT,
  -- 'empty' = exit 0 ama 0 kayıt scrape edildi (add_bot_runs_records_written.sql)
  status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'timeout', 'skipped', 'empty')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  duration_seconds NUMERIC,
  exit_code INTEGER,
  summary TEXT,
  stdout_excerpt TEXT,
  stderr_excerpt TEXT,
  -- Scrape edilen kayıt sayısı; DB'ye yazılan satır sayısı değil
  records_written INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS bot_runs_created_at_idx ON public.bot_runs (created_at DESC);
CREATE INDEX IF NOT EXISTS bot_runs_bot_name_idx ON public.bot_runs (bot_name, created_at DESC);

ALTER TABLE public.bot_runs ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON public.bot_runs TO authenticated;

DROP POLICY IF EXISTS "admins read bot runs" ON public.bot_runs;
CREATE POLICY "admins read bot runs"
ON public.bot_runs
FOR SELECT
TO authenticated
USING (public.is_fullet_admin());

CREATE TABLE IF NOT EXISTS public.system_alerts (
  id BIGSERIAL PRIMARY KEY,
  severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
  source TEXT NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS system_alerts_status_created_idx
ON public.system_alerts (status, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS system_alerts_open_source_title_idx
ON public.system_alerts (source, title)
WHERE status = 'open';

ALTER TABLE public.system_alerts ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON public.system_alerts TO authenticated;

DROP POLICY IF EXISTS "admins read system alerts" ON public.system_alerts;
CREATE POLICY "admins read system alerts"
ON public.system_alerts
FOR SELECT
TO authenticated
USING (public.is_fullet_admin());
