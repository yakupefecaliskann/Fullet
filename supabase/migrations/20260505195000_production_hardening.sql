-- ==============================================================================
-- LEGACY MIGRATION WARNING
-- ==============================================================================
-- This migration predates the current visibility_status / price_status release
-- flow. Keep it for migration history only. Do not paste this file manually into
-- the production Supabase SQL editor. Use database/add_status_columns.sql,
-- database/create_postgis_rpc.sql and database/rls_policies.sql instead.
-- ==============================================================================

-- Fullet production hardening migration.

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS istasyonlar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marka TEXT NOT NULL,
    isim TEXT NOT NULL,
    il TEXT,
    ilce TEXT,
    adres TEXT,
    enlem DOUBLE PRECISION,
    boylam DOUBLE PRECISION,
    konum GEOGRAPHY(POINT, 4326),
    aktif BOOLEAN NOT NULL DEFAULT TRUE,
    veri_kaynagi TEXT,
    olusturulma_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    guncellenme_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fiyatlar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    istasyon_id UUID NOT NULL REFERENCES istasyonlar(id) ON DELETE CASCADE,
    yakit_tipi TEXT NOT NULL,
    fiyat NUMERIC(10, 2) NOT NULL,
    son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    veri_kaynagi TEXT
);

CREATE TABLE IF NOT EXISTS fiyat_gecmisi (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    istasyon_id UUID NOT NULL REFERENCES istasyonlar(id) ON DELETE CASCADE,
    yakit_tipi TEXT NOT NULL,
    eski_fiyat NUMERIC(10, 2),
    yeni_fiyat NUMERIC(10, 2) NOT NULL,
    fiyat_farki NUMERIC(10, 2),
    degisim_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS haberler (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baslik TEXT NOT NULL,
    link TEXT NOT NULL,
    kaynak TEXT,
    tarih TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    olusturulma_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS push_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'fcm',
    cihaz_id TEXT,
    olusturulma_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE istasyonlar
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS aktif BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS veri_kaynagi TEXT,
    ADD COLUMN IF NOT EXISTS guncellenme_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE fiyatlar
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS veri_kaynagi TEXT;

ALTER TABLE fiyat_gecmisi
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE haberler
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE push_tokens
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'fcm',
    ADD COLUMN IF NOT EXISTS cihaz_id TEXT,
    ADD COLUMN IF NOT EXISTS son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Data repair before constraints/indexes.
UPDATE istasyonlar
SET
  enlem = NULL,
  boylam = NULL,
  konum = NULL
WHERE (enlem IS NULL) <> (boylam IS NULL)
   OR enlem NOT BETWEEN 35 AND 43
   OR boylam NOT BETWEEN 25 AND 46;

UPDATE istasyonlar
SET
  marka = TRIM(marka),
  isim = TRIM(isim),
  il = NULLIF(TRIM(il), ''),
  ilce = NULLIF(TRIM(ilce), '')
WHERE TRUE;

UPDATE fiyatlar
SET
  yakit_tipi = CASE
    WHEN yakit_tipi ILIKE '%lpg%' OR yakit_tipi ILIKE '%otogaz%' OR yakit_tipi ILIKE '%oto gaz%' THEN 'LPG'
    WHEN yakit_tipi ILIKE '%motorin%' OR yakit_tipi ILIKE '%dizel%' THEN 'Motorin'
    WHEN yakit_tipi ILIKE '%benzin%' OR yakit_tipi ILIKE '%kursunsuz%' OR yakit_tipi ILIKE '%95%' THEN 'Kursunsuz 95'
    ELSE TRIM(yakit_tipi)
  END,
  son_guncelleme = COALESCE(son_guncelleme, NOW())
WHERE TRUE;

DELETE FROM fiyatlar
WHERE fiyat IS NULL
   OR fiyat <= 0
   OR fiyat >= 300
   OR istasyon_id IS NULL
   OR yakit_tipi IS NULL
   OR TRIM(yakit_tipi) = '';

WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY istasyon_id, yakit_tipi
      ORDER BY son_guncelleme DESC NULLS LAST, id DESC
    ) AS rn
  FROM fiyatlar
)
DELETE FROM fiyatlar f
USING ranked r
WHERE f.id = r.id
  AND r.rn > 1;

WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY link
      ORDER BY tarih DESC NULLS LAST, olusturulma_tarihi DESC NULLS LAST, id DESC
    ) AS rn
  FROM haberler
  WHERE link IS NOT NULL
)
DELETE FROM haberler h
USING ranked r
WHERE h.id = r.id
  AND r.rn > 1;

DELETE FROM haberler
WHERE link IS NULL
   OR TRIM(link) = ''
   OR baslik IS NULL
   OR TRIM(baslik) = '';

UPDATE push_tokens
SET
  provider = CASE
    WHEN token LIKE 'ExpoPushToken[%]' OR token LIKE 'ExponentPushToken[%]' THEN 'expo'
    ELSE COALESCE(provider, 'fcm')
  END,
  son_guncelleme = COALESCE(son_guncelleme, NOW())
WHERE TRUE;

DELETE FROM push_tokens
WHERE token IS NULL
   OR length(token) < 20
   OR length(token) > 4096
   OR COALESCE(provider, 'fcm') NOT IN ('fcm', 'expo', 'apns');

WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY token
      ORDER BY son_guncelleme DESC NULLS LAST, olusturulma_tarihi DESC NULLS LAST, id DESC
    ) AS rn
  FROM push_tokens
)
DELETE FROM push_tokens p
USING ranked r
WHERE p.id = r.id
  AND r.rn > 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fiyatlar_istasyon_yakit_unique'
    ) THEN
        ALTER TABLE fiyatlar
            ADD CONSTRAINT fiyatlar_istasyon_yakit_unique UNIQUE (istasyon_id, yakit_tipi);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fiyatlar_fiyat_positive'
    ) THEN
        ALTER TABLE fiyatlar
            ADD CONSTRAINT fiyatlar_fiyat_positive CHECK (fiyat > 0 AND fiyat < 300);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'istasyonlar_lat_lng_valid'
    ) THEN
        ALTER TABLE istasyonlar
            ADD CONSTRAINT istasyonlar_lat_lng_valid CHECK (
                (enlem IS NULL AND boylam IS NULL)
                OR (enlem BETWEEN 35 AND 43 AND boylam BETWEEN 25 AND 46)
            );
    END IF;

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

CREATE UNIQUE INDEX IF NOT EXISTS haberler_link_unique_idx ON haberler(link);
CREATE INDEX IF NOT EXISTS istasyonlar_konum_idx ON istasyonlar USING GIST(konum);
CREATE INDEX IF NOT EXISTS istasyonlar_brand_city_idx ON istasyonlar(marka, il, ilce);
CREATE INDEX IF NOT EXISTS fiyatlar_istasyon_idx ON fiyatlar(istasyon_id);
CREATE INDEX IF NOT EXISTS fiyat_gecmisi_istasyon_tarih_idx ON fiyat_gecmisi(istasyon_id, degisim_tarihi DESC);
CREATE INDEX IF NOT EXISTS haberler_tarih_idx ON haberler(tarih DESC);
CREATE UNIQUE INDEX IF NOT EXISTS push_tokens_token_unique_idx ON push_tokens(token);
CREATE INDEX IF NOT EXISTS push_tokens_provider_idx ON push_tokens(provider);

CREATE OR REPLACE FUNCTION set_istasyon_konum()
RETURNS trigger AS $$
BEGIN
  IF NEW.enlem IS NOT NULL AND NEW.boylam IS NOT NULL THEN
    NEW.konum := ST_SetSRID(ST_MakePoint(NEW.boylam, NEW.enlem), 4326)::geography;
  ELSE
    NEW.konum := NULL;
  END IF;
  NEW.guncellenme_tarihi := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_konum ON istasyonlar;
CREATE TRIGGER trigger_set_konum
BEFORE INSERT OR UPDATE OF enlem, boylam ON istasyonlar
FOR EACH ROW
EXECUTE FUNCTION set_istasyon_konum();

UPDATE istasyonlar
SET konum = ST_SetSRID(ST_MakePoint(boylam, enlem), 4326)::geography
WHERE enlem IS NOT NULL
  AND boylam IS NOT NULL
  AND (
    konum IS NULL
    OR ST_X(konum::geometry) IS DISTINCT FROM boylam
    OR ST_Y(konum::geometry) IS DISTINCT FROM enlem
  );

CREATE OR REPLACE FUNCTION log_fiyat_degisimi()
RETURNS trigger AS $$
BEGIN
  IF OLD.fiyat IS DISTINCT FROM NEW.fiyat THEN
    NEW.son_guncelleme := NOW();
    INSERT INTO fiyat_gecmisi (
      istasyon_id,
      yakit_tipi,
      eski_fiyat,
      yeni_fiyat,
      fiyat_farki,
      degisim_tarihi
    ) VALUES (
      OLD.istasyon_id,
      OLD.yakit_tipi,
      OLD.fiyat,
      NEW.fiyat,
      ROUND(NEW.fiyat - OLD.fiyat, 2),
      NOW()
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_fiyat_guncelleme ON fiyatlar;
CREATE TRIGGER trigger_fiyat_guncelleme
BEFORE UPDATE ON fiyatlar
FOR EACH ROW
EXECUTE FUNCTION log_fiyat_degisimi();

CREATE OR REPLACE FUNCTION get_nearby_stations(
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  max_dist_meters INT DEFAULT 20000,
  max_results INT DEFAULT 250
)
RETURNS SETOF istasyonlar
LANGUAGE sql
STABLE
AS $$
  SELECT *
  FROM istasyonlar
  WHERE aktif = TRUE
    AND konum IS NOT NULL
    AND lat BETWEEN 35 AND 43
    AND lng BETWEEN 25 AND 46
    AND ST_DWithin(
      konum,
      ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
      LEAST(GREATEST(max_dist_meters, 1000), 100000)
    )
  ORDER BY konum <-> ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
  LIMIT LEAST(GREATEST(max_results, 1), 500);
$$;

GRANT EXECUTE ON FUNCTION get_nearby_stations(DOUBLE PRECISION, DOUBLE PRECISION, INT, INT) TO anon, authenticated;

ALTER TABLE istasyonlar ENABLE ROW LEVEL SECURITY;
ALTER TABLE fiyatlar ENABLE ROW LEVEL SECURITY;
ALTER TABLE fiyat_gecmisi ENABLE ROW LEVEL SECURITY;
ALTER TABLE haberler ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read istasyonlar" ON istasyonlar;
DROP POLICY IF EXISTS "public read fiyatlar" ON fiyatlar;
DROP POLICY IF EXISTS "public read fiyat_gecmisi" ON fiyat_gecmisi;
DROP POLICY IF EXISTS "public read haberler" ON haberler;
DROP POLICY IF EXISTS "anon insert push token" ON push_tokens;

DROP POLICY IF EXISTS "Herkese acik okuma (istasyonlar)" ON istasyonlar;
DROP POLICY IF EXISTS "Herkese acik okuma (fiyatlar)" ON fiyatlar;
DROP POLICY IF EXISTS "Herkese acik okuma (fiyat_gecmisi)" ON fiyat_gecmisi;
DROP POLICY IF EXISTS "Herkese acik okuma (haberler)" ON haberler;
DROP POLICY IF EXISTS "Kullanicilar sadece cihaz ekleyebilir" ON push_tokens;
DROP POLICY IF EXISTS "Sadece oturum acan cihazlar push token ekleyebilir" ON push_tokens;
DROP POLICY IF EXISTS "Sadece oturum açan cihazlar push token ekleyebilir" ON push_tokens;

CREATE POLICY "public read istasyonlar" ON istasyonlar FOR SELECT TO anon, authenticated USING (aktif = TRUE);
CREATE POLICY "public read fiyatlar" ON fiyatlar FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read fiyat_gecmisi" ON fiyat_gecmisi FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read haberler" ON haberler FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "anon insert push token" ON push_tokens
  FOR INSERT TO anon, authenticated
  WITH CHECK (
    length(token) BETWEEN 20 AND 4096
    AND provider IN ('fcm', 'expo', 'apns')
  );

NOTIFY pgrst, 'reload schema';

COMMIT;
