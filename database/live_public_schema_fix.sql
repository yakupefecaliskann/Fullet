-- Fullet live public schema fix.
-- Run this in Supabase SQL Editor for project xhkvlwecsacfjpbtyqcc.
-- It is intentionally small and fully public-qualified.

SET search_path = public, extensions;

CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE public.istasyonlar
  ADD COLUMN IF NOT EXISTS aktif BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS veri_kaynagi TEXT,
  ADD COLUMN IF NOT EXISTS guncellenme_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS konum GEOGRAPHY(POINT, 4326);

ALTER TABLE public.fiyatlar
  ADD COLUMN IF NOT EXISTS veri_kaynagi TEXT;

ALTER TABLE public.push_tokens
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'fcm',
  ADD COLUMN IF NOT EXISTS son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE public.push_tokens
SET
  provider = CASE
    WHEN token LIKE 'ExpoPushToken[%]' OR token LIKE 'ExponentPushToken[%]' THEN 'expo'
    ELSE COALESCE(provider, 'fcm')
  END,
  son_guncelleme = COALESCE(son_guncelleme, NOW())
WHERE TRUE;

WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY token
      ORDER BY son_guncelleme DESC NULLS LAST, olusturulma_tarihi DESC NULLS LAST, id DESC
    ) AS rn
  FROM public.push_tokens
  WHERE token IS NOT NULL
)
DELETE FROM public.push_tokens p
USING ranked r
WHERE p.id = r.id
  AND r.rn > 1;

UPDATE public.istasyonlar
SET aktif = TRUE
WHERE aktif IS NULL;

UPDATE public.istasyonlar
SET konum = ST_SetSRID(ST_MakePoint(boylam, enlem), 4326)::geography
WHERE enlem IS NOT NULL
  AND boylam IS NOT NULL
  AND enlem BETWEEN 35 AND 43
  AND boylam BETWEEN 25 AND 46
  AND (
    konum IS NULL
    OR ST_X(konum::geometry) IS DISTINCT FROM boylam
    OR ST_Y(konum::geometry) IS DISTINCT FROM enlem
  );

CREATE INDEX IF NOT EXISTS istasyonlar_konum_idx
ON public.istasyonlar USING GIST(konum);

CREATE INDEX IF NOT EXISTS fiyatlar_istasyon_idx
ON public.fiyatlar(istasyon_id);

CREATE UNIQUE INDEX IF NOT EXISTS push_tokens_token_unique_idx
ON public.push_tokens(token);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fiyatlar_istasyon_yakit_unique'
  ) THEN
    ALTER TABLE public.fiyatlar
      ADD CONSTRAINT fiyatlar_istasyon_yakit_unique UNIQUE (istasyon_id, yakit_tipi);
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.set_istasyon_konum()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
  IF NEW.enlem IS NOT NULL AND NEW.boylam IS NOT NULL THEN
    NEW.konum := ST_SetSRID(ST_MakePoint(NEW.boylam, NEW.enlem), 4326)::geography;
  ELSE
    NEW.konum := NULL;
  END IF;
  NEW.guncellenme_tarihi := NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_set_konum ON public.istasyonlar;
CREATE TRIGGER trigger_set_konum
BEFORE INSERT OR UPDATE OF enlem, boylam ON public.istasyonlar
FOR EACH ROW
EXECUTE FUNCTION public.set_istasyon_konum();

DROP FUNCTION IF EXISTS public.get_nearby_stations(DOUBLE PRECISION, DOUBLE PRECISION, INTEGER);

CREATE OR REPLACE FUNCTION public.get_nearby_stations(
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  max_dist_meters INTEGER DEFAULT 20000,
  max_results INTEGER DEFAULT 250
)
RETURNS SETOF public.istasyonlar
LANGUAGE sql
STABLE
SET search_path = public, extensions
AS $$
  SELECT i.*
  FROM public.istasyonlar AS i
  WHERE i.aktif IS TRUE
    AND i.konum IS NOT NULL
    AND lat BETWEEN 35 AND 43
    AND lng BETWEEN 25 AND 46
    AND ST_DWithin(
      i.konum,
      ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
      LEAST(GREATEST(max_dist_meters, 1000), 100000)
    )
  ORDER BY i.konum <-> ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
  LIMIT LEAST(GREATEST(max_results, 1), 500);
$$;

GRANT EXECUTE ON FUNCTION public.get_nearby_stations(
  DOUBLE PRECISION,
  DOUBLE PRECISION,
  INTEGER,
  INTEGER
) TO anon, authenticated;

ALTER TABLE public.istasyonlar ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fiyatlar ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fiyat_gecmisi ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.haberler ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.push_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read istasyonlar" ON public.istasyonlar;
DROP POLICY IF EXISTS "public read fiyatlar" ON public.fiyatlar;
DROP POLICY IF EXISTS "public read fiyat_gecmisi" ON public.fiyat_gecmisi;
DROP POLICY IF EXISTS "public read haberler" ON public.haberler;
DROP POLICY IF EXISTS "anon insert push token" ON public.push_tokens;
DROP POLICY IF EXISTS "Herkese acik okuma (istasyonlar)" ON public.istasyonlar;
DROP POLICY IF EXISTS "Herkese acik okuma (fiyatlar)" ON public.fiyatlar;
DROP POLICY IF EXISTS "Herkese acik okuma (fiyat_gecmisi)" ON public.fiyat_gecmisi;
DROP POLICY IF EXISTS "Herkese acik okuma (haberler)" ON public.haberler;
DROP POLICY IF EXISTS "Kullanicilar sadece cihaz ekleyebilir" ON public.push_tokens;
DROP POLICY IF EXISTS "Sadece oturum acan cihazlar push token ekleyebilir" ON public.push_tokens;
DROP POLICY IF EXISTS "Sadece oturum açan cihazlar push token ekleyebilir" ON public.push_tokens;

CREATE POLICY "public read istasyonlar"
ON public.istasyonlar
FOR SELECT
TO anon, authenticated
USING (aktif IS TRUE);

CREATE POLICY "public read fiyatlar"
ON public.fiyatlar
FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "public read fiyat_gecmisi"
ON public.fiyat_gecmisi
FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "public read haberler"
ON public.haberler
FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "anon insert push token"
ON public.push_tokens
FOR INSERT
TO anon, authenticated
WITH CHECK (
  length(token) BETWEEN 20 AND 4096
  AND COALESCE(provider, 'fcm') IN ('fcm', 'expo', 'apns')
);

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
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname = 'get_nearby_stations'
      AND pg_get_function_identity_arguments(p.oid) =
        'lat double precision, lng double precision, max_dist_meters integer, max_results integer'
  ) AS nearby_rpc_max_results_exists,
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
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relname = 'istasyonlar'
      AND c.relrowsecurity = TRUE
  ) AS istasyonlar_rls_enabled;
