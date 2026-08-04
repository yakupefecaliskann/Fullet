-- Çok markalı karantina zenginleştirmesi öncesi yedek (4 Ağustos 2026).
CREATE TABLE public._yedek_20260804_karantina_oncesi AS
SELECT * FROM public.istasyonlar
WHERE marka IN ('Opet', 'Petrol Ofisi', 'Aytemiz');

ALTER TABLE public._yedek_20260804_karantina_oncesi ENABLE ROW LEVEL SECURITY;
