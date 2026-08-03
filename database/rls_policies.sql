-- !! BAYAT BOLUM UYARISI — 3 Agustos 2026 !!
-- Bu dosyanin `push_tokens` bolumleri artik gecersiz: tablo kaldirildi
-- (bkz. supabase/migrations/20260803150000_drop_push_infrastructure.sql).

-- Fullet Row Level Security policies.
-- Public app users may read app data. Writes stay behind service role keys.

CREATE TABLE IF NOT EXISTS push_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT 'fcm',
  cihaz_id TEXT,
  olusturulma_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE push_tokens
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'fcm',
  ADD COLUMN IF NOT EXISTS cihaz_id TEXT,
  ADD COLUMN IF NOT EXISTS son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE push_tokens
SET
  provider = CASE
    WHEN token LIKE 'ExpoPushToken[%]' OR token LIKE 'ExponentPushToken[%]' THEN 'expo'
    ELSE COALESCE(provider, 'fcm')
  END,
  son_guncelleme = COALESCE(son_guncelleme, NOW())
WHERE TRUE;

ALTER TABLE istasyonlar ENABLE ROW LEVEL SECURITY;
ALTER TABLE istasyonlar FORCE ROW LEVEL SECURITY;
ALTER TABLE fiyatlar ENABLE ROW LEVEL SECURITY;
ALTER TABLE fiyat_gecmisi ENABLE ROW LEVEL SECURITY;
ALTER TABLE haberler ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_tokens ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
  policy_record RECORD;
BEGIN
  FOR policy_record IN
    SELECT schemaname, tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('istasyonlar', 'fiyatlar', 'fiyat_gecmisi', 'haberler', 'push_tokens')
  LOOP
    EXECUTE format(
      'DROP POLICY IF EXISTS %I ON %I.%I',
      policy_record.policyname,
      policy_record.schemaname,
      policy_record.tablename
    );
  END LOOP;
END $$;

CREATE POLICY "public read istasyonlar"
ON public.istasyonlar FOR SELECT
TO anon, authenticated
USING (aktif IS TRUE AND visibility_status IN ('visible', 'low_priority'));

CREATE POLICY "restrict active istasyonlar"
ON public.istasyonlar AS RESTRICTIVE
FOR SELECT
TO anon, authenticated
USING (aktif IS TRUE AND visibility_status IN ('visible', 'low_priority'));

CREATE POLICY "public read fiyatlar"
ON public.fiyatlar FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "public read fiyat_gecmisi"
ON public.fiyat_gecmisi FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "public read haberler"
ON public.haberler FOR SELECT
TO anon, authenticated
USING (true);

-- anon rolüne push token INSERT izni verilmiyor: hiçbir istemci (Flutter
-- uygulaması dahil) şu an push_tokens'a yazmıyor, bu yüzden anon'a açık
-- INSERT yalnızca kimliksiz doldurma (spam) riski taşıyan gereksiz bir
-- yüzeydi. Sprint 4'te gerçek cihaz token kaydı eklendiğinde bu
-- authenticated politikası (Firebase/Supabase JWT şartlı) yeterli olacak.
CREATE POLICY "authenticated insert push token"
ON public.push_tokens FOR INSERT
TO authenticated
WITH CHECK (
  length(token) BETWEEN 20 AND 4096
  AND COALESCE(provider, 'fcm') IN ('fcm', 'expo', 'apns')
);

REVOKE INSERT ON public.push_tokens FROM anon;

NOTIFY pgrst, 'reload schema';
