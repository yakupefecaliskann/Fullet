-- Fullet admin observability API grants.
-- Run after the admin observability tables are created.
-- RLS still protects the rows; these grants only make the tables visible to
-- authenticated Supabase users so admin policies can run.

GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT ON public.admin_emails TO authenticated;
GRANT SELECT ON public.app_heartbeats TO authenticated;
GRANT SELECT ON public.bot_runs TO authenticated;
GRANT SELECT ON public.system_alerts TO authenticated;

GRANT EXECUTE ON FUNCTION public.is_fullet_admin() TO authenticated;
GRANT EXECUTE ON FUNCTION public.record_app_heartbeat(UUID, TEXT, TEXT) TO anon, authenticated;

NOTIFY pgrst, 'reload schema';

SELECT
  has_table_privilege('authenticated', 'public.admin_emails', 'SELECT') AS admin_emails_select_ok,
  has_table_privilege('authenticated', 'public.app_heartbeats', 'SELECT') AS app_heartbeats_select_ok,
  has_table_privilege('authenticated', 'public.bot_runs', 'SELECT') AS bot_runs_select_ok,
  has_table_privilege('authenticated', 'public.system_alerts', 'SELECT') AS system_alerts_select_ok,
  has_function_privilege('authenticated', 'public.is_fullet_admin()', 'EXECUTE') AS is_admin_execute_ok,
  has_function_privilege('anon', 'public.record_app_heartbeat(UUID, TEXT, TEXT)', 'EXECUTE') AS heartbeat_anon_execute_ok;
