-- =============================================================================
-- `low_priority` TEK YÖNLÜ KAPANINI KAPAT — 4 Ağustos 2026
-- =============================================================================
-- ÖLÇÜM (4 Ağustos sabah sağlık kontrolü, canlı veri):
--
--   2702 aktif istasyonun 989'u (%36,6) `low_priority` damgalıydı.
--   Bu 989'un HEPSİNİN gösterilebilir fiyatı vardı; 939'u `fresh` ve son
--   12 saat içinde doğrulanmıştı. Yani veri tertemizdi, damga haksızdı.
--
--   Marka dağılımı:  TotalEnergies 776/811 (%95)  Shell 174  TP 39
--
-- KÖK NEDEN:
--   `database_writes.py` eskiden dokunduğu her istasyona koşulsuz
--   `low_priority` yazıyordu (kod yorumu: "canlıda 1.052 satır"). Bu yazma
--   3 Ağustos'ta durduruldu, ama MEVCUT DAMGALAR TEMİZLENMEDİ.
--
-- ASIL ARIZA — kapan tek yönlüydü:
--   JOB 5 (fullet-resolve-station-visibility) yalnızca hidden -> visible,
--   JOB 3 (fullet-hide-stale-stations)        yalnızca visible -> low_priority.
--   `low_priority` -> `visible` geçişini yapan HİÇBİR mekanizma yoktu.
--   Fiyat sonsuza kadar taze kalsa bile istasyon geri dönemiyordu.
--
-- NEDEN ŞİMDİ ACIDI:
--   Faz 3 / madde 21'e kadar `low_priority` uygulamada ölüydü. Artık
--   `smart_station_service.dart:59` bu istasyonları "en ucuz" motorundan
--   tamamen dışlıyor. Yani 3 Ağustos'ta doğru yapılan düzeltme, farkında
--   olmadan Total'in %95'ini fiyat karşılaştırmasından çıkardı.
--
-- =============================================================================
-- SALINIM (flip-flop) RİSKİ VE ÇÖZÜMÜ — bu dosyanın en kritik kısmı
-- =============================================================================
-- Geri dönüş kolunu körlemesine eklemek istasyonları her gün
-- visible <-> low_priority arasında salındırırdı:
--
--   JOB 3 muafiyeti:  price_status='fresh' AND son_guncelleme > 7 gün
--   Geri dönüş kolu:  price_status IN ('fresh','stale')
--
-- Bu iki yüklem AYNI DEĞİL. Fiyatı `stale` olan bir istasyonu JOB 3 gece
-- düşürür, geri dönüş kolu bir saat sonra kaldırır, ertesi gece yine düşer.
--
-- Üstelik JOB 3'ün yüklemi `son_guncelleme` kullanıyordu — scraper/freshness.py
-- bunun TAM OLARAK yanlış kolon olduğunu belgeliyor:
--     son_guncelleme = fiyatın son DEĞİŞTİĞİ an
--     son_dogrulama  = fiyatı son DOĞRULADIĞIMIZ an
-- Türkiye'de fiyatlar ayda birkaç kez değişir. Yani her gün doğrulanan ama
-- 7 gündür değişmeyen bir fiyat, JOB 3'ün gözünde "bayat"tı. JOB 5 ve 6 bu
-- hata için düzeltilmişti (COALESCE(son_dogrulama, son_guncelleme)), JOB 3
-- atlanmıştı. Total'in %95'inin damgalanması bununla uyumlu.
--
-- ÇÖZÜM: iki job'ı AYNI YÜKLEME bağla — "gösterilebilir fiyatı var mı?"
--   JOB 3 düşürür:      ... AND gösterilebilir fiyatı YOK
--   JOB 5d döndürür:    ... AND gösterilebilir fiyatı VAR
-- Bir istasyon ikisini birden karşılayamaz. Salınım matematiksel olarak
-- imkansız hale gelir. "Gösterilebilir" tanımı JOB 5a/5b ile birebir aynıdır:
-- price_status IN ('fresh','stale')  (tazelik eşikleri freshness.py'de).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) TEK SEFERLİK DÜZELTME: haksız damgaları kaldır.
--    Ölçüldü: 989 istasyonun 989'u gösterilebilir fiyata sahip, yani hepsi
--    geri dönecek; fiyatsız kalıp hidden'a düşecek olan YOK.
-- -----------------------------------------------------------------------------
UPDATE public.istasyonlar i
SET visibility_status = 'visible'
WHERE i.visibility_status = 'low_priority'
  AND i.aktif = TRUE
  AND EXISTS (
      SELECT 1 FROM public.fiyatlar f
      WHERE f.istasyon_id = i.id
        AND f.price_status IN ('fresh', 'stale')
  );

-- -----------------------------------------------------------------------------
-- 2) KALICI GERİ DÖNÜŞ KOLU: JOB 5'e 5d adımını ekle.
--    Artık kapan iki yönlü; damga fiyat tazelendiği anda kendiliğinden kalkar.
-- -----------------------------------------------------------------------------
SELECT cron.unschedule('fullet-resolve-station-visibility');

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

    -- 5d) GERİ DÖNÜŞ KOLU (4 Ağustos 2026): fiyatı tazelenen `low_priority`
    --     istasyonu `visible`'a döndür. JOB 3 ile aynı yükleme bağlı olduğu
    --     için salınım üretmez — yukarıdaki açıklamaya bak.
    UPDATE public.istasyonlar i
    SET visibility_status = 'visible'
    WHERE i.visibility_status = 'low_priority'
      AND i.aktif = TRUE
      AND EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      );
    $$
);

-- -----------------------------------------------------------------------------
-- 3) JOB 3'ü 5d ile SİMETRİK hale getir.
--    Değişen: `son_guncelleme`/`fresh` yüklemi -> "gösterilebilir fiyat" yüklemi.
--    Job'ın amacı aynı kalıyor (7 gündür dokunulmamış ölü envanteri soluklaştır),
--    yalnızca tazelik dilini sistemin geri kalanıyla hizalıyoruz.
-- -----------------------------------------------------------------------------
SELECT cron.unschedule('fullet-hide-stale-stations');

SELECT cron.schedule(
    'fullet-hide-stale-stations',
    '0 3 * * *',
    $$
    UPDATE public.istasyonlar i
    SET visibility_status = 'low_priority'
    WHERE i.visibility_status = 'visible'
      AND i.aktif = TRUE
      AND i.guncellenme_tarihi < NOW() - INTERVAL '7 days'
      AND NOT EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      );
    $$
);
