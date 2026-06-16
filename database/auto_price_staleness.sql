-- =============================================================================
-- Fullet: Otomatik Fiyat Eskitme (pg_cron)
-- =============================================================================
-- Supabase Dashboard > SQL Editor'da çalıştır.
-- pg_cron extension Supabase'de varsayılan olarak aktif gelir.
-- Bu migration idempotent'tir — defalarca çalıştırılabilir.
-- =============================================================================

-- 1. pg_cron extension'ı etkinleştir (zaten aktifse hata vermez)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Mevcut job'ları temizle (idempotent yeniden çalıştırma için)
SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname IN (
    'fullet-mark-stale-prices',
    'fullet-mark-unknown-prices',
    'fullet-cleanup-push-tokens',
    'fullet-hide-stale-stations'
);

-- =============================================================================
-- JOB 1: fresh → stale (her saat başı çalışır)
-- 12 saatten eski "fresh" fiyatları "stale" statüsüne taşır.
-- Botlar çalışmazsa kullanıcı eski fiyatı "güncel" sanmaz.
-- =============================================================================
SELECT cron.schedule(
    'fullet-mark-stale-prices',
    '5 * * * *',  -- Her saat başında :05'te
    $$
    UPDATE public.fiyatlar
    SET price_status = 'stale'
    WHERE price_status = 'fresh'
      AND son_guncelleme < NOW() - INTERVAL '12 hours';
    $$
);

-- =============================================================================
-- JOB 2: stale → unknown (her saat başı çalışır)
-- 48 saatten eski "stale" fiyatları "unknown" statüsüne taşır.
-- Bu fiyatlar UI'da "fiyat bilinmiyor" olarak gösterilir.
-- =============================================================================
SELECT cron.schedule(
    'fullet-mark-unknown-prices',
    '10 * * * *',  -- Her saat başında :10'da
    $$
    UPDATE public.fiyatlar
    SET price_status = 'unknown'
    WHERE price_status = 'stale'
      AND son_guncelleme < NOW() - INTERVAL '48 hours';
    $$
);

-- =============================================================================
-- JOB 3: Aktif ama güncellenmemiş istasyonları low_priority'ye al (günde 1)
-- 7 gündür hiç fiyat güncellemesi almamış "visible" istasyonları düşür.
-- Haritada yanlış/eski konumlu istasyonlar görünürlüğünü kaybeder.
-- =============================================================================
SELECT cron.schedule(
    'fullet-hide-stale-stations',
    '0 3 * * *',  -- Her gün 03:00'te
    $$
    UPDATE public.istasyonlar
    SET visibility_status = 'low_priority'
    WHERE visibility_status = 'visible'
      AND aktif = TRUE
      AND guncellenme_tarihi < NOW() - INTERVAL '7 days'
      AND id NOT IN (
          -- Son 7 günde fresh fiyatı olan istasyonları koru
          SELECT DISTINCT istasyon_id
          FROM public.fiyatlar
          WHERE price_status = 'fresh'
            AND son_guncelleme > NOW() - INTERVAL '7 days'
      );
    $$
);

-- =============================================================================
-- JOB 4: Push token temizleme (haftada 1, pazar 04:00)
-- 90 günde hiç kullanılmamış token'ları sil.
-- =============================================================================
SELECT cron.schedule(
    'fullet-cleanup-push-tokens',
    '0 4 * * 0',  -- Her pazar 04:00'te
    $$
    DELETE FROM public.push_tokens
    WHERE olusturulma_tarihi < NOW() - INTERVAL '90 days';
    $$
);

-- =============================================================================
-- Doğrulama: Kayıtlı job'ları listele
-- =============================================================================
SELECT
    jobid,
    jobname,
    schedule,
    command,
    active
FROM cron.job
WHERE jobname LIKE 'fullet-%'
ORDER BY jobname;
