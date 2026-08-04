-- F4-3 (Petrol Ofisi) akıtması öncesi geri-alma yedeği (4 Ağustos 2026).
-- Mevcut 80 PO kaydı güncellenebilir, ~2.582 yeni kayıt eklenecek.
-- Bu fazın en büyük tek yazması; geri alınabilir olmalı.
CREATE TABLE public._yedek_20260804_po_oncesi AS
SELECT * FROM public.istasyonlar WHERE marka = 'Petrol Ofisi';

ALTER TABLE public._yedek_20260804_po_oncesi ENABLE ROW LEVEL SECURITY;
