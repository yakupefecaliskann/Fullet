-- =============================================================================
-- BP kalıcı olarak envanterden çıkarıldı (10 Kasım 2026 denetimi, §G-K1)
-- =============================================================================
-- Petrol Ofisi BP Türkiye'yi devraldı; marka dönüşümü 1 Kasım 2026'da bitti
-- (bkz. scraper/po_station_bot.py). Fiyat sayfası
-- petrolofisi.com.tr/akaryakit-fiyatlari-bp 23 Ekim'den beri 404, envanter botu
-- da hiç olmadı. 37 istasyon fiyatsız ve gizli duruyordu.
--
-- Silme öncesi: 37 istasyon, 111 fiyat, 4740 geçmiş satırı, 0 favori, 0 fiyat
-- alarmı. Yerel yedek: backup_bp_20261110.json (gitignore'da).
-- fiyatlar, fiyat_gecmisi ve price_alerts FK'leri ON DELETE CASCADE.
--
-- Koruma: beklenenden fazla satır görülürse hiçbir şey silinmez.
-- =============================================================================

DO $$
DECLARE
  adet integer;
  gorunur integer;
BEGIN
  SELECT count(*), count(*) FILTER (WHERE visibility_status <> 'hidden')
    INTO adet, gorunur
    FROM public.istasyonlar
   WHERE marka = 'BP';
  IF adet > 50 OR gorunur > 0 THEN
    RAISE EXCEPTION 'BP silme durduruldu: % satir, % gorunur', adet, gorunur;
  END IF;
END $$;

DELETE FROM public.istasyonlar WHERE marka = 'BP';

UPDATE public.system_alerts
   SET status = 'resolved', resolved_at = now()
 WHERE status = 'open'
   AND (source = 'bot:bp_bot.py' OR (source = 'ops_report' AND title = 'BP'));
