-- =============================================================================
-- Fullet: bot_runs'a 'degraded' status
-- =============================================================================
-- Supabase Dashboard > SQL Editor'da çalıştır. Idempotent'tir.
--
-- Amaç (Faz 0 denetimi, hedef kapsaması boşluğu):
--   Faz 0 yalnızca "bot HİÇ kayıt üretmedi mi?" sorusunu görünür kıldı
--   ('empty'). "Bot hedeflerinin çoğunu kaybetti mi?" sorusu sorulmuyordu.
--
--   shell_bot her koşuda 150 hedeften ~95'ini "Element is not visible" ile
--   sessizce atlayıp yine de yüzlerce kayıt döndürüyordu; dolayısıyla
--   'success' görünüyordu. Canlı sonuç: Shell'in 1.152 fiyat satırının
--   yalnızca %26'sı taze, %36'sı bayat, %38'i bilinmiyor — diğer altı
--   markada bayat SIFIR.
--
--   'degraded' = "veri yazıldı ama eksik". 'success' yalanı ile 'failed'
--   abartısı arasındaki eksik durum. Pipeline'ı kırmızıya döndürmez; bot_runs
--   ve system_alerts üzerinden görünür kalır.
--   Eşik: db_utils.MIN_TARGET_COVERAGE (%70).
-- =============================================================================

ALTER TABLE public.bot_runs
  DROP CONSTRAINT IF EXISTS bot_runs_status_check;

ALTER TABLE public.bot_runs
  ADD CONSTRAINT bot_runs_status_check
  CHECK (status IN ('success', 'failed', 'timeout', 'skipped', 'empty', 'degraded'));

NOTIFY pgrst, 'reload schema';

-- Doğrulama
SELECT pg_get_constraintdef(oid) AS status_check
FROM pg_constraint
WHERE conname = 'bot_runs_status_check';
