-- =============================================================================
-- Fullet: bot_runs'a targets_ok / targets_total kolonlari
-- =============================================================================
-- Supabase Dashboard > SQL Editor'da calistir. Idempotent'tir.
--
-- Amac (Faz 0-2 denetimi, bulgu 2):
--   D1 hedef kapsamasini olcuyor ve dusukse 'degraded' isaretliyor, ama
--   SAYILAR hicbir yerde kalici degildi:
--
--     telemetry._compact_log stdout'un ILK 4000 karakterini saklar;
--     '[RECORDS] ... targets_ok=A targets_total=B' satiri ~150 hedeflik
--     kosunun SONUNDA basilir. Canli olcum: 20 shell_bot kaydinin
--     HICBIRINDE kapsama satiri yok.
--
--   Sonuc: kapsama yalnizca system_alerts.metadata'da, o da yalnizca
--   'degraded' kosular icin kaliyordu. BASARILI bir kosuda %71 mi %100 mu
--   oldugu gorulemiyordu — yani esige dogru TREND izlenemiyordu. Ironik
--   olan: D1 teshisi tam da stdout_excerpt okunarak yapilmisti; o yontem
--   duzeltmeden sonra artik calismiyor.
--
--   Bu kolonlar her kosuda (basarili dahil) kapsamayi sorgulanabilir yapar:
--     SELECT started_at, targets_ok, targets_total,
--            round(100.0 * targets_ok / targets_total) AS kapsama_yuzde
--     FROM bot_runs
--     WHERE bot_name = 'shell_bot.py' AND targets_total IS NOT NULL
--     ORDER BY started_at DESC;
--
--   NULL = bot hedef tabanli calismiyor (opet/total/tp gibi tek istekle tum
--   ulkeyi cekenler) ya da eski format. 0 hedef ile karistirilmamali.
-- =============================================================================

ALTER TABLE public.bot_runs
  ADD COLUMN IF NOT EXISTS targets_ok INTEGER;

ALTER TABLE public.bot_runs
  ADD COLUMN IF NOT EXISTS targets_total INTEGER;

COMMENT ON COLUMN public.bot_runs.targets_ok IS
  'Basariyla okunan hedef (il/ilce) sayisi. NULL = bot hedef tabanli degil.';

COMMENT ON COLUMN public.bot_runs.targets_total IS
  'Planlanan hedef sayisi. targets_ok/targets_total < db_utils.MIN_TARGET_COVERAGE ise status=degraded.';

NOTIFY pgrst, 'reload schema';

-- Dogrulama
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'bot_runs'
  AND column_name IN ('targets_ok', 'targets_total')
ORDER BY column_name;
