-- F4-4 (Aytemiz) akıtması öncesi geri-alma yedeği (4 Ağustos 2026).
-- Mevcut 35 Aytemiz kaydı güncellenebilir, ~871 yeni kayıt eklenecek.
CREATE TABLE public._yedek_20260804_aytemiz_oncesi AS
SELECT * FROM public.istasyonlar WHERE marka = 'Aytemiz';

ALTER TABLE public._yedek_20260804_aytemiz_oncesi ENABLE ROW LEVEL SECURITY;
