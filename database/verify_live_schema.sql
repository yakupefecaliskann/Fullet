-- Run this in Supabase SQL Editor after production_hardening.sql.
-- It verifies that the live database schema contains the release-critical pieces.

NOTIFY pgrst, 'reload schema';

SELECT
  EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'istasyonlar'
      AND column_name = 'aktif'
  ) AS istasyonlar_aktif_exists,
  EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'fiyatlar'
      AND column_name = 'veri_kaynagi'
  ) AS fiyatlar_veri_kaynagi_exists,
  EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'push_tokens'
      AND column_name = 'provider'
  ) AS push_tokens_provider_exists,
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname = 'get_nearby_stations'
      AND pg_get_function_identity_arguments(p.oid) =
        'lat double precision, lng double precision, max_dist_meters integer, max_results integer'
  ) AS nearby_rpc_max_results_exists,
  EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relname = 'istasyonlar'
      AND c.relrowsecurity = TRUE
  ) AS istasyonlar_rls_enabled,
  EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relname = 'istasyonlar'
      AND c.relforcerowsecurity = TRUE
  ) AS istasyonlar_force_rls_enabled,
  EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'istasyonlar'
      AND policyname = 'public read istasyonlar'
      AND roles @> ARRAY['anon']::name[]
      AND qual ILIKE '%aktif%'
  ) AS istasyonlar_anon_policy_filters_active,
  EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'istasyonlar'
      AND policyname = 'restrict active istasyonlar'
      AND permissive = 'RESTRICTIVE'
      AND roles @> ARRAY['anon']::name[]
      AND qual ILIKE '%aktif%'
  ) AS istasyonlar_restrictive_active_policy,
  NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'istasyonlar'
      AND policyname NOT IN ('public read istasyonlar', 'restrict active istasyonlar')
      AND cmd IN ('SELECT', 'ALL')
      AND (
        roles @> ARRAY['anon']::name[]
        OR roles @> ARRAY['authenticated']::name[]
        OR roles @> ARRAY['public']::name[]
      )
  ) AS istasyonlar_no_extra_public_read_policy;
