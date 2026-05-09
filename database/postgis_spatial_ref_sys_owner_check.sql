-- Read-only diagnostic for Supabase Security Advisor's spatial_ref_sys warning.
-- Safe to run. It does not modify anything.

SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  pg_get_userbyid(c.relowner) AS table_owner,
  c.relrowsecurity AS rls_enabled,
  e.extname AS extension_name,
  en.nspname AS extension_schema,
  has_table_privilege('anon', 'public.spatial_ref_sys', 'SELECT') AS anon_can_select,
  has_table_privilege('authenticated', 'public.spatial_ref_sys', 'SELECT') AS authenticated_can_select
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_depend d
  ON d.objid = c.oid
  AND d.deptype = 'e'
LEFT JOIN pg_extension e ON e.oid = d.refobjid
LEFT JOIN pg_namespace en ON en.oid = e.extnamespace
WHERE n.nspname = 'public'
  AND c.relname = 'spatial_ref_sys';
