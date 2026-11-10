-- =============================================================================
-- fiyat_gecmisi embed'i için bileşik indeks (10 Kasım 2026 denetimi, §G-O1)
-- =============================================================================
-- Uygulama istasyon listesine "son 20 fiyat değişimi"ni gömüyor. Eski plan her
-- istasyonun tüm geçmişini okuyup sıralıyordu: 1000 istasyonda 5,3 sn. anon
-- zaman aşımı 3 sn, authenticated 8 sn olduğu için canlıda günde birkaç 500
-- üretiyordu. Sıra, PostgREST'in ürettiği ORDER BY ile birebir aynı olmalı.
-- =============================================================================

CREATE INDEX IF NOT EXISTS fiyat_gecmisi_istasyon_tarih_idx
  ON public.fiyat_gecmisi (istasyon_id, degisim_tarihi DESC NULLS LAST);
