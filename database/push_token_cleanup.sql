-- Push token temizleme — standalone versiyon
-- auto_price_staleness.sql zaten bu job'ı içeriyor.
-- Sadece manuel temizlik için kullan.

DELETE FROM public.push_tokens
WHERE olusturulma_tarihi < NOW() - INTERVAL '90 days';

SELECT COUNT(*) AS remaining_tokens FROM public.push_tokens;
