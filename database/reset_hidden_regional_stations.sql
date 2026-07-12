-- =============================================================================
-- Fullet: Regional Brand Hidden Station Reset
-- =============================================================================
-- SORUN: add_status_columns.sql migration'ı çalıştığında aktif=false olan
-- tüm istasyonları visibility_status='hidden' yaptı.
--
-- Bu, bölgesel scraper'ların (bp_bot, po_bot, aytemiz_bot, tp_bot) web sitesinde
-- listelemeyen veya Turkish karakter normalizasyon uyuşmazlığı nedeniyle
-- eşleştiremeyen şehirlerdeki istasyonları kalıcı olarak gizledi.
--
-- ÇÖZÜM: Bu markaların hidden istasyonlarını 'visible' olarak sıfırla.
-- Sonuç:
--   - Bir sonraki scraper çalışmasında eşleşen istasyonlar → fresh fiyat alır
--   - Eşleşmeyen istasyonlar → visible kalır ama fiyat yok (gri marker)
--   - 7 gün sonra pg_cron → low_priority'ye düşürür (hala haritada görünür)
--
-- RİSK: Kapalı/geçersiz istasyonlar görünür hale gelebilir. Ancak 7 gün içinde
-- pg_cron bunları low_priority'ye indirir. Scraper'lar aktif olduğu şehirlerde
-- zaten visibility'i yönetiyor.
--
-- Supabase SQL Editor'da çalıştır. İdempotent'tir.
-- =============================================================================

-- Etkilenecek satır sayısını önce kontrol et:
SELECT marka, COUNT(*) as hidden_count
FROM public.istasyonlar
WHERE visibility_status = 'hidden'
  AND marka IN ('BP', 'Petrol Ofisi', 'Aytemiz', 'Türkiye Petrolleri')
GROUP BY marka
ORDER BY hidden_count DESC;

-- Reset işlemini çalıştır:
UPDATE public.istasyonlar
SET
    visibility_status = 'visible',
    guncellenme_tarihi = NOW()
WHERE visibility_status = 'hidden'
  AND marka IN ('BP', 'Petrol Ofisi', 'Aytemiz', 'Türkiye Petrolleri');

-- Sonuç doğrulaması:
SELECT marka, visibility_status, COUNT(*) as count
FROM public.istasyonlar
WHERE marka IN ('BP', 'Petrol Ofisi', 'Aytemiz', 'Türkiye Petrolleri')
GROUP BY marka, visibility_status
ORDER BY marka, visibility_status;
