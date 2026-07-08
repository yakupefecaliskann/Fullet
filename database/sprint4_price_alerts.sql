-- =============================================================================
-- Fullet Sprint 4: Kişisel Fiyat Alarmları
-- =============================================================================
-- Supabase SQL Editor'da çalıştır. İdempotent'tir.
-- =============================================================================

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

-- SÜPERSEDE EDİLDİ: bkz. database/sprint4_users_favorites.sql — bu satır
-- price_alerts'i RLS'siz, anon'a tam CRUD açık bırakıyordu. Aşağıdaki GRANT
-- artık geçerli değil; RLS + authenticated-only erişim sprint4_users_favorites.sql
-- içinde tanımlı. Bu satır yalnızca geçmiş referans için burada bırakıldı.
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.price_alerts TO authenticated, anon;

NOTIFY pgrst, 'reload schema';

-- Doğrulama:
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'price_alerts' ORDER BY ordinal_position;
