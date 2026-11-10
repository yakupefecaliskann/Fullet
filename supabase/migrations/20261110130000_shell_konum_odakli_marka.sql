-- =============================================================================
-- Shell istasyonları fiyatsız, konum olarak görünür (10 Kasım 2026, §G-K4)
-- =============================================================================
-- Shell'in resmi fiyat kaynağı 9 Eylül 2026'da kapandı, yerine resmi kanal yok.
-- Ürün kararı: istasyonlar haritada kalsın, fiyat gösterilmesin. 3 Ağustos'taki
-- "fiyatı olmayanı hiç gösterme" kuralına tek ve bilinçli istisna budur.
--
-- Eski fiyatlar `unknown` kalır. Uygulama `unknown` fiyatı göstermez ve en ucuz /
-- en mantıklı hesabına katmaz (Station.displayPriceFor, FuelPrice.isDisplayable).
--
-- Resmi bir Shell kaynağı bulunursa: bu istisnaları kaldırın, başka değişiklik
-- gerekmez. Kaynak: database/auto_price_staleness.sql aynı kuralı taşır.
-- =============================================================================

SELECT cron.schedule(
    'fullet-resolve-station-visibility',
    '15 * * * *',
    $job$
    UPDATE public.istasyonlar i
    SET visibility_status = 'hidden'
    WHERE i.visibility_status <> 'hidden'
      AND i.marka <> 'Shell'
      AND NOT EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      );

    UPDATE public.istasyonlar i
    SET visibility_status = 'visible'
    WHERE i.visibility_status = 'hidden'
      AND i.aktif = TRUE
      AND (i.marka = 'Shell' OR EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      ));

    UPDATE public.istasyonlar
    SET visibility_status = 'hidden'
    WHERE aktif = FALSE AND visibility_status <> 'hidden';

    UPDATE public.istasyonlar i
    SET visibility_status = 'visible'
    WHERE i.visibility_status = 'low_priority'
      AND i.aktif = TRUE
      AND (i.marka = 'Shell' OR EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      ));
    $job$
);

SELECT cron.schedule(
    'fullet-hide-stale-stations',
    '0 3 * * *',
    $job$
    UPDATE public.istasyonlar i
    SET visibility_status = 'low_priority'
    WHERE i.visibility_status = 'visible'
      AND i.aktif = TRUE
      AND i.marka <> 'Shell'
      AND i.guncellenme_tarihi < NOW() - INTERVAL '7 days'
      AND NOT EXISTS (
          SELECT 1 FROM public.fiyatlar f
          WHERE f.istasyon_id = i.id
            AND f.price_status IN ('fresh', 'stale')
      );
    $job$
);

CREATE OR REPLACE VIEW public.marka_kullanilabilirlik
WITH (security_invoker = true) AS
SELECT
  i.marka,
  COUNT(*)::int AS istasyon_sayisi
FROM public.istasyonlar i
WHERE i.aktif IS TRUE
  AND i.visibility_status IN ('visible', 'low_priority')
  AND (i.marka = 'Shell' OR EXISTS (
    SELECT 1
    FROM public.fiyatlar f
    WHERE f.istasyon_id = i.id
      AND f.price_status IN ('fresh', 'stale')
  ))
GROUP BY i.marka;

UPDATE public.istasyonlar
   SET visibility_status = 'visible'
 WHERE marka = 'Shell' AND aktif = TRUE AND visibility_status = 'hidden';

UPDATE public.system_alerts
   SET status = 'resolved', resolved_at = now()
 WHERE status = 'open'
   AND (source = 'bot:shell_bot.py' OR (source = 'ops_report' AND title = 'Shell'));
