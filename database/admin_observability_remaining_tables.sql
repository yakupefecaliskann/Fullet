-- Fullet admin panel remaining observability tables.
-- Run this if app_heartbeats works but the panel says bot_runs/system_alerts
-- could not be found in the schema cache.

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

CREATE TABLE IF NOT EXISTS public.bot_runs (
  id BIGSERIAL PRIMARY KEY
);

ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS bot_name TEXT;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS run_mode TEXT;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS duration_seconds NUMERIC;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS exit_code INTEGER;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS stdout_excerpt TEXT;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS stderr_excerpt TEXT;
ALTER TABLE public.bot_runs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.bot_runs DROP CONSTRAINT IF EXISTS bot_runs_status_check;
ALTER TABLE public.bot_runs
ADD CONSTRAINT bot_runs_status_check
CHECK (status IN ('success', 'failed', 'timeout', 'skipped'));

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
  id BIGSERIAL PRIMARY KEY
);

ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS severity TEXT;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open';
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;

ALTER TABLE public.system_alerts DROP CONSTRAINT IF EXISTS system_alerts_severity_check;
ALTER TABLE public.system_alerts
ADD CONSTRAINT system_alerts_severity_check
CHECK (severity IN ('info', 'warning', 'error', 'critical'));

ALTER TABLE public.system_alerts DROP CONSTRAINT IF EXISTS system_alerts_status_check;
ALTER TABLE public.system_alerts
ADD CONSTRAINT system_alerts_status_check
CHECK (status IN ('open', 'resolved'));

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

NOTIFY pgrst, 'reload schema';

SELECT
  to_regclass('public.app_heartbeats') IS NOT NULL AS app_heartbeats_ok,
  to_regclass('public.bot_runs') IS NOT NULL AS bot_runs_ok,
  to_regclass('public.system_alerts') IS NOT NULL AS system_alerts_ok;
