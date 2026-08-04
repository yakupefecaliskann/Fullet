-- F4-1 akıtması öncesi geri-alma yedeği (4 Ağustos 2026).
-- Akıtma 387 mevcut kaydı GÜNCELLEYECEK (isim/adres/koordinat) ve ~785 yeni
-- kayıt ekleyecek. Güncelleme geri alınabilir olmalı.
CREATE TABLE public._yedek_20260804_opet_oncesi AS
SELECT * FROM public.istasyonlar WHERE marka = 'Opet';

-- 3 Ağustos dersinin gereği: yedek tablo RLS'siz bırakılmaz. Politika
-- eklenmiyor, yani yalnızca service_role erişir; anon/authenticated kapalı.
ALTER TABLE public._yedek_20260804_opet_oncesi ENABLE ROW LEVEL SECURITY;
