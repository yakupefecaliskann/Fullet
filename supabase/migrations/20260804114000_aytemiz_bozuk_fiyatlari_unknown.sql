-- Aytemiz'in fiyat kaynağı piyasa gerçeğiyle uyuşmuyor (4 Ağustos 2026):
--   sayfa : Benzin 64,86 / Motorin 67,17
--   piyasa: Benzin 68,20 / Motorin 82,14
-- Sayfa "Son Güncelleme: 04.08.2026 13:52" diyor, yani bayat değil — yanlış.
-- İç tutarsızlık da bunu doğruluyor: Aytemiz'de benzin-motorin farkı 2,31 ₺,
-- diğer tüm markalarda ~14 ₺.
--
-- Sanity gate motorini reddetti ama benzin eşiği geçti (%4,9 < %10) ve 81 ilin
-- 79'unda "en ucuz" çıkarak kullanıcıyı yanlış istasyona yönlendiriyordu.
--
-- SİLİNMİYOR, `unknown`a çekiliyor: geri alınabilir ve kaynak düzelirse bot
-- yeniden `fresh` yazar. JOB 5a istasyonları kendiliğinden gizler; fiyat
-- geldiği an 875 istasyon haritaya döner.
--
-- Kalıcı düzeltme sanity_gate.py'deki KAYNAK BÜTÜNLÜĞÜ kuralıdır.
UPDATE public.fiyatlar f
SET price_status = 'unknown'
FROM public.istasyonlar i
WHERE i.id = f.istasyon_id
  AND i.marka = 'Aytemiz'
  AND f.price_status <> 'unknown';

UPDATE public.istasyonlar i
SET visibility_status = 'hidden'
WHERE i.visibility_status <> 'hidden'
  AND NOT EXISTS (
      SELECT 1 FROM public.fiyatlar f
      WHERE f.istasyon_id = i.id AND f.price_status IN ('fresh', 'stale')
  );
