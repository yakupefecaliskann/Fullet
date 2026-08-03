-- =============================================================================
-- Fullet: Otomatik Fiyat Eskitme ve Görünürlük Kuralı (pg_cron)
-- =============================================================================
-- Supabase Dashboard > SQL Editor'da çalıştır.
-- pg_cron extension Supabase'de varsayılan olarak aktif gelir.
-- Bu script idempotent'tir — defalarca çalıştırılabilir.
--
-- !! DİKKAT — 3 Ağustos 2026 DRIFT ONARIMI !!
-- Bu dosya CANLI ile UYUŞMUYORDU. Faz 1'de `son_dogrulama` kolonu eklendiğinde
-- JOB 1/2 canlıda `COALESCE(son_dogrulama, son_guncelleme)`ye çevrildi ama bu
-- DOSYA `son_guncelleme` demeye devam ediyordu. Dosyayı yeniden çalıştıran biri
-- Faz 1'in en değerli düzeltmesini geri alır ve fiyatların `fresh -> stale ->
-- fresh` salınımı geri gelirdi (doğru fiyat "⚠️ Bayat" bandıyla gösterilir).
-- Artık dosya canlının aynısıdır. Değiştirirken ikisini birlikte değiştir.
-- =============================================================================

-- 1. pg_cron extension'ı etkinleştir (zaten aktifse hata vermez)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Mevcut job'ları temizle (idempotent yeniden çalıştırma için)
--    'fullet-cleanup-push-tokens' KASTEN listede: push altyapısı kaldırıldı
--    (yol haritası madde 22/23), bu job artık kurulmuyor ve varsa siliniyor.
SELECT cron.unschedule(jobid)
FROM cron.job
WHERE jobname IN (
    'fullet-mark-stale-prices',
    'fullet-mark-unknown-prices',
    'fullet-cleanup-push-tokens',
    'fullet-hide-stale-stations',
    'fullet-resolve-station-visibility'
);

-- =============================================================================
-- JOB 1: fresh → stale (her saat :05)
-- 12 saatten eski "fresh" fiyatları "stale" statüsüne taşır.
--
-- Eşik kolonu `son_dogrulama`'dır: fiyat DEĞİŞMESE de bot her doğruladığında
-- ilerler. `son_guncelleme` yalnızca fiyat DEĞİŞTİĞİNDE ilerler (trigger öyle
-- yazıyor); ona bakmak, aylardır değişmeyen doğru bir fiyatı bayat sayardı.
-- COALESCE, kolonun henüz dolmadığı eski satırlar için geri düşüş.
-- =============================================================================
SELECT cron.schedule(
    'fullet-mark-stale-prices',
    '5 * * * *',
    $$
    UPDATE public.fiyatlar SET price_status = 'stale'
    WHERE price_status = 'fresh'
      AND COALESCE(son_dogrulama, son_guncelleme) < NOW() - INTERVAL '12 hours';
    $$
);

-- =============================================================================
-- JOB 2: stale → unknown (her saat :10)
-- 48 saatten eski "stale" fiyatlar "bilinmiyor"a düşer; uygulamada gösterilmez.
-- =============================================================================
SELECT cron.schedule(
    'fullet-mark-unknown-prices',
    '10 * * * *',
    $$
    UPDATE public.fiyatlar SET price_status = 'unknown'
    WHERE price_status = 'stale'
      AND COALESCE(son_dogrulama, son_guncelleme) < NOW() - INTERVAL '48 hours';
    $$
);

-- =============================================================================
-- JOB 5: Görünürlüğü FİYAT DURUMUNDAN türet (her saat :15)
-- =============================================================================
-- Neden var (3 Ağustos 2026):
--
--   * Shell'in 178 aktif ve görünür istasyonunun hiçbir gösterilebilir fiyatı
--     yoktu; kullanıcı haritada o pinlere basınca "Yok" görüyordu. Karar:
--     fiyatı olmayanı göstermektense hiç göstermemek daha dürüst.
--   * `aktif` ve `visibility_status` birbirinden bağımsız yazılıyordu ve
--     canlıda çelişiyorlardı: 232 satır "aktif ama hidden", 354 satır
--     "pasif ama visible".
--
-- Bu job GERİ DÖNDÜRÜLEBİLİR olmak zorunda: Shell'in hedef listesi dönerek
-- ilerliyor, bugün kuyrukta olan ilçe yarın öne geliyor. 5b olmasaydı her tur
-- kalıcı olarak istasyon kaybederdik.
--
-- Tek kural:  fiyatı yok  -> hidden        (5a)
--             fiyatı var  -> visible       (5b, yalnızca gizliyken)
--             pasif       -> daima hidden  (5c)
-- `low_priority` KASTEN korunur — o JOB 3'ün kararıdır (aşağı bak).
-- =============================================================================
SELECT cron.schedule(
    'fullet-resolve-station-visibility',
    '15 * * * *',
    $$
    -- 5a) Gösterilebilir fiyatı olmayanı gizle.
    UPDATE public.istasyonlar i
    SET visibility_status = 'hidden'
    WHERE i.visibility_status <> 'hidden'
      AND NOT EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      );

    -- 5b) Fiyatı geri gelen gizli istasyonu geri getir.
    UPDATE public.istasyonlar i
    SET visibility_status = 'visible'
    WHERE i.visibility_status = 'hidden'
      AND i.aktif = TRUE
      AND EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      );

    -- 5c) Pasif istasyon asla görünür olmaz.
    UPDATE public.istasyonlar
    SET visibility_status = 'hidden'
    WHERE aktif = FALSE AND visibility_status <> 'hidden';
    $$
);

-- =============================================================================
-- JOB 3: Konumu şüpheli istasyonları low_priority'ye al (her gün 03:00)
-- 7 gündür hiç güncellenmemiş "visible" istasyonları düşürür.
--
-- Faz 3 / madde 21'e kadar bu mekanizma ÖLÜYDÜ: uygulama `low_priority`'yi
-- normal `visible` gibi gösteriyordu. Artık uygulamada gerçek karşılığı var
-- (marker soluk, "en ucuz" yarışında yer almaz), dolayısıyla job anlamlı.
--
-- JOB 5 ile çakışmaz: JOB 5 yalnızca hidden <-> visible geçişi yapar,
-- `low_priority`'ye dokunmaz.
-- =============================================================================
SELECT cron.schedule(
    'fullet-hide-stale-stations',
    '0 3 * * *',
    $$
    UPDATE public.istasyonlar
    SET visibility_status = 'low_priority'
    WHERE visibility_status = 'visible'
      AND aktif = TRUE
      AND guncellenme_tarihi < NOW() - INTERVAL '7 days'
      AND id NOT IN (
          SELECT DISTINCT istasyon_id
          FROM public.fiyatlar
          WHERE price_status = 'fresh'
            AND son_guncelleme > NOW() - INTERVAL '7 days'
      );
    $$
);

-- =============================================================================
-- JOB 4 (push token temizliği) KALDIRILDI — 3 Ağustos 2026.
-- Push altyapısı uçtan uca kopuktu ve kaldırıldı: `push_tokens` tablosunda 0
-- satır vardı, Flutter uygulaması `firebase_messaging` kullanmıyordu ve tabloya
-- hiç yazmıyordu. Job'un kendisi de hatalıydı — yorumu "90 gündür KULLANILMAMIŞ
-- token" derken kodu `olusturulma_tarihi`'ne bakıyordu, yani 90 günlük SADIK
-- kullanıcının token'ını siliyordu. Yukarıdaki unschedule listesi onu temizler.
-- =============================================================================

-- =============================================================================
-- Doğrulama: kayıtlı job'ları listele
-- =============================================================================
SELECT jobid, jobname, schedule, active
FROM cron.job
WHERE jobname LIKE 'fullet-%'
ORDER BY jobname;
