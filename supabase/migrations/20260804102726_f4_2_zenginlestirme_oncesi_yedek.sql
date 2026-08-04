-- F4-2 zenginleştirme öncesi geri-alma yedeği (4 Ağustos 2026).
-- 25 kaydın isim/adres/il/ilçe/koordinatı API verisiyle ÜZERİNE YAZILACAK.
-- Geri alınabilir olmalı: yanlış eşleşme eski kaydın kimliğini yok eder.
CREATE TABLE public._yedek_20260804_f42_oncesi AS
SELECT * FROM public.istasyonlar WHERE marka = 'Opet';

ALTER TABLE public._yedek_20260804_f42_oncesi ENABLE ROW LEVEL SECURITY;
