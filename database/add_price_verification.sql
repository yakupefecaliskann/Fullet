-- !! BAYAT BOLUM UYARISI — 3 Agustos 2026 !!
-- Bu dosyadaki push_tokens temizlik job'u artik gecersiz: tablo kaldirildi
-- (bkz. supabase/migrations/20260803150000_drop_push_infrastructure.sql).

-- =============================================================================
-- Fullet: fiyatlar.son_dogrulama + tek tazelik tanımı
-- =============================================================================
-- Supabase Dashboard > SQL Editor'da çalıştır. Idempotent'tir.
--
-- SORUN (yol haritası S0-3 / S0-4):
--   `son_guncelleme` iki farklı anlamda kullanılıyordu:
--     * trigger log_fiyat_degisimi -> "fiyatın son DEĞİŞTİĞİ an"
--     * pg_cron tazelik işleri     -> "fiyatı son DOĞRULADIĞIMIZ an"
--   Fiyatlar ayda birkaç kez değiştiği için bu ikisi haftalarca ayrışıyor.
--   Üstüne bot diff'i değişmemiş fiyatı hiç yazmıyordu; 12 saatlik cron eşiği
--   de DOĞRU fiyatı bayat işaretliyordu. 1 Ağustos canlı verisi bu döngüyü
--   doğruladı (Opet/PO/Aytemiz/TP: 22:13'te yazılmış, ertesi koşuda atlanmış,
--   10:14'te bayada düşmüş, 0 taze fiyat).
--
-- ÇÖZÜM:
--   son_guncelleme -> yalnızca fiyat DEĞİŞTİĞİNDE ilerler (trigger zaten öyle)
--   son_dogrulama  -> her başarılı kazımada ilerler (bot yazar)
--   Tazelik işleri son_dogrulama'ya bakar.
--
-- Eşikler scraper/freshness.py ile AYNI olmalı (birlikte değiştirilir):
--   FRESH_MAX_HOURS = 12   |   STALE_MAX_HOURS = 48
-- =============================================================================

-- 1. Kolon + geriye dönük doldurma ---------------------------------------------
ALTER TABLE public.fiyatlar
  ADD COLUMN IF NOT EXISTS son_dogrulama TIMESTAMPTZ;

COMMENT ON COLUMN public.fiyatlar.son_dogrulama IS
  'Fiyatın kaynaktan son DOĞRULANDIĞI an (değişmese de ilerler). Tazelik bu kolona bakar; son_guncelleme yalnızca fiyat değişiminde ilerler.';

-- Mevcut satırlar için elimizdeki en iyi tahmin son_guncelleme'dir.
UPDATE public.fiyatlar
SET son_dogrulama = son_guncelleme
WHERE son_dogrulama IS NULL;

ALTER TABLE public.fiyatlar
  ALTER COLUMN son_dogrulama SET DEFAULT NOW();

CREATE INDEX IF NOT EXISTS fiyatlar_son_dogrulama_idx
  ON public.fiyatlar (son_dogrulama DESC);

-- 2. Tazelik cron işlerini son_dogrulama'ya taşı --------------------------------
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname IN ('fullet-mark-stale-prices', 'fullet-mark-unknown-prices');

-- fresh -> stale : 12 saattir doğrulanmamış
SELECT cron.schedule(
    'fullet-mark-stale-prices',
    '5 * * * *',
    $$
    UPDATE public.fiyatlar
    SET price_status = 'stale'
    WHERE price_status = 'fresh'
      AND COALESCE(son_dogrulama, son_guncelleme) < NOW() - INTERVAL '12 hours';
    $$
);

-- stale -> unknown : 48 saattir doğrulanmamış
SELECT cron.schedule(
    'fullet-mark-unknown-prices',
    '10 * * * *',
    $$
    UPDATE public.fiyatlar
    SET price_status = 'unknown'
    WHERE price_status = 'stale'
      AND COALESCE(son_dogrulama, son_guncelleme) < NOW() - INTERVAL '48 hours';
    $$
);

-- 3. Push token temizliği: doğru kolona bak (yol haritası S3-4) -----------------
-- Yorum "90 günde hiç KULLANILMAMIŞ token" diyordu ama kod olusturulma_tarihi'ne
-- bakıyordu; 90 günlük sadık kullanıcının token'ı siliniyordu.
SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname = 'fullet-cleanup-push-tokens';

SELECT cron.schedule(
    'fullet-cleanup-push-tokens',
    '0 4 * * 0',
    $$
    DELETE FROM public.push_tokens
    WHERE COALESCE(son_guncelleme, olusturulma_tarihi) < NOW() - INTERVAL '90 days';
    $$
);

NOTIFY pgrst, 'reload schema';

-- =============================================================================
-- Doğrulama
-- =============================================================================
SELECT jobname, schedule, active FROM cron.job
WHERE jobname LIKE 'fullet-%' ORDER BY jobname;

SELECT
  COUNT(*) AS toplam,
  COUNT(son_dogrulama) AS dogrulama_dolu,
  COUNT(*) FILTER (WHERE price_status = 'fresh') AS taze
FROM public.fiyatlar;
