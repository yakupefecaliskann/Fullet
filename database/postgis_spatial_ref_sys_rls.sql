-- Fix Supabase Security Advisor: "RLS Disabled in Public" for PostGIS metadata.
--
-- public.spatial_ref_sys is created by PostGIS and contains coordinate system
-- definitions, not user data. Supabase still flags it because the public schema
-- is exposed through the Data API. This enables RLS without adding public
-- policies, so anon/authenticated clients cannot read it directly.
--
-- Important: on some Supabase projects this table is owned by the PostGIS
-- extension owner, not by the SQL Editor role. In that case this script fails
-- with "must be owner of table spatial_ref_sys". That is expected and should not
-- be worked around with DROP EXTENSION on a live app, because PostGIS backs the
-- station location column and nearby-station RPCs.
--
-- After running this, click "Rerun linter" in Supabase Security Advisor.

ALTER TABLE public.spatial_ref_sys ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.spatial_ref_sys FROM anon;
REVOKE ALL ON TABLE public.spatial_ref_sys FROM authenticated;

NOTIFY pgrst, 'reload schema';

SELECT
  c.relrowsecurity AS spatial_ref_sys_rls_enabled,
  has_table_privilege('anon', 'public.spatial_ref_sys', 'SELECT') AS anon_can_select_spatial_ref_sys,
  has_table_privilege('authenticated', 'public.spatial_ref_sys', 'SELECT') AS authenticated_can_select_spatial_ref_sys
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = 'spatial_ref_sys';
