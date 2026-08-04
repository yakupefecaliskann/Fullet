-- 4 Ağustos 2026: 3 Ağustos temizliğinin geri-alma yedekleri artık gereksiz.
-- Doğrulandı: hiçbir satırı canlı tabloda yok (544/729 kayıt, 0 hâlâ canlıda).
-- RLS kapalıydı; Supabase linter'ı 4 tabloyu da ERROR seviyesinde işaretliyordu.
DROP TABLE IF EXISTS public._yedek_20260803_pasif_istasyonlar;
DROP TABLE IF EXISTS public._yedek_20260803_pasif_fiyatlar;
DROP TABLE IF EXISTS public._yedek_20260803_pasif_gecmis;
DROP TABLE IF EXISTS public._yedek_20260803_eski_gecmis;

-- Nisan 2026 LPG kolon hatasından kalan moloz: 90+ gündür `unknown`.
-- Doğrulandı: 58 satırın hepsi LPG ve HİÇBİRİ istasyonu fiyatsız bırakmıyor
-- (her istasyonun ayrıca fresh/stale fiyatı var), yani harita kaybı olmaz.
DELETE FROM public.fiyatlar
WHERE price_status = 'unknown'
  AND son_dogrulama < NOW() - INTERVAL '90 days';
