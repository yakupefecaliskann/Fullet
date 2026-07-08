-- =============================================================================
-- Fullet — fullet_users / fullet_favorites şema + RLS
-- =============================================================================
-- Supabase SQL Editor'da çalıştır. İdempotent'tir.
--
-- BAĞLAM: fullet_users ve fullet_favorites tabloları bugüne kadar repo'da
-- hiçbir CREATE TABLE tanımına sahip değildi (muhtemelen Dashboard'dan elle
-- oluşturuldu) ve RLS'siz, anon role tam CRUD açık durumdaydı. Bu dosya hem
-- şemayı versiyon kontrolüne kazandırıyor hem de RLS'i devreye alıyor.
--
-- ÖN KOŞUL: Bu dosyayı çalıştırmadan önce Supabase Dashboard →
-- Authentication → Sign In / Providers → Third Party Auth → Firebase
-- sağlayıcısının eklenmiş olması VE uygulamanın yeni sürümünün
-- (main.dart accessToken callback'i içeren) dağıtılmış olması gerekir.
-- Aksi halde auth.jwt()->>'sub' hep NULL döner ve authenticated kullanıcılar
-- dahi kendi verisine erişemez.
--
-- NOT: price_alerts tablosunu da (henüz canlıda oluşturulmamışsa) burada
-- idempotent olarak yaratıyoruz — Sprint 4 (database/sprint4_price_alerts.sql)
-- henüz çalıştırılmamış olabilir, bu dosya çalıştırma sırasına bağımlı olmasın
-- diye price_alerts şemasını da içeriyor (sprint4_price_alerts.sql ile birebir).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.fullet_users (
  firebase_uid   TEXT PRIMARY KEY,
  display_name   TEXT,
  email          TEXT,
  avatar_url     TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.fullet_favorites (
  firebase_uid   TEXT NOT NULL,
  station_id     UUID NOT NULL REFERENCES public.istasyonlar(id) ON DELETE CASCADE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (firebase_uid, station_id)
);

CREATE INDEX IF NOT EXISTS fullet_favorites_uid_idx
  ON public.fullet_favorites (firebase_uid);

CREATE TABLE IF NOT EXISTS public.price_alerts (
  id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id              TEXT NOT NULL,
  istasyon_id          UUID REFERENCES public.istasyonlar(id) ON DELETE CASCADE,
  yakit_tipi           TEXT NOT NULL,
  esik_fiyat           DECIMAL(10, 2) NOT NULL,
  aktif                BOOLEAN DEFAULT TRUE,
  olusturulma_tarihi   TIMESTAMPTZ DEFAULT NOW(),
  son_tetiklenme       TIMESTAMPTZ,
  push_token           TEXT
);

CREATE INDEX IF NOT EXISTS price_alerts_aktif_idx
  ON public.price_alerts (istasyon_id, yakit_tipi) WHERE aktif = TRUE;

CREATE INDEX IF NOT EXISTS price_alerts_user_idx
  ON public.price_alerts (user_id);

-- =============================================================================
-- RLS
-- =============================================================================

ALTER TABLE public.fullet_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fullet_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_alerts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "kullanici kendi profilini yonetir" ON public.fullet_users;
CREATE POLICY "kullanici kendi profilini yonetir" ON public.fullet_users
  FOR ALL TO authenticated
  USING (firebase_uid = auth.jwt() ->> 'sub')
  WITH CHECK (firebase_uid = auth.jwt() ->> 'sub');

DROP POLICY IF EXISTS "kullanici kendi favorilerini yonetir" ON public.fullet_favorites;
CREATE POLICY "kullanici kendi favorilerini yonetir" ON public.fullet_favorites
  FOR ALL TO authenticated
  USING (firebase_uid = auth.jwt() ->> 'sub')
  WITH CHECK (firebase_uid = auth.jwt() ->> 'sub');

DROP POLICY IF EXISTS "kullanici kendi alarmlarini yonetir" ON public.price_alerts;
CREATE POLICY "kullanici kendi alarmlarini yonetir" ON public.price_alerts
  FOR ALL TO authenticated
  USING (user_id = auth.jwt() ->> 'sub')
  WITH CHECK (user_id = auth.jwt() ->> 'sub');

-- Artık anon değil, sadece authenticated (Firebase Third Party Auth ile
-- doğrulanmış) rolüne erişim veriyoruz. Misafir (girişsiz) kullanıcı zaten
-- bu üç tabloya hiç dokunmuyor — favoriler/alarmlar yalnızca SharedPreferences
-- ile yerel kalıyor, giriş yapılınca senkronlanıyor (bkz. modern_map_screen.dart
-- _handleSignIn / mergeRemoteFavorites).
GRANT SELECT, INSERT, UPDATE, DELETE ON public.fullet_users TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.fullet_favorites TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.price_alerts TO authenticated;

REVOKE ALL ON public.fullet_users FROM anon;
REVOKE ALL ON public.fullet_favorites FROM anon;
REVOKE ALL ON public.price_alerts FROM anon;

NOTIFY pgrst, 'reload schema';

-- =============================================================================
-- Doğrulama
-- =============================================================================
-- RLS açık mı?
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname IN ('fullet_users', 'fullet_favorites', 'price_alerts');

-- anon'un artık erişimi yok mu? (boş satır dönmeli)
SELECT table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_name IN ('fullet_users', 'fullet_favorites', 'price_alerts')
  AND grantee = 'anon';
