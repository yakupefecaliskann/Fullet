-- =============================================================================
-- Fullet: bot_runs'a records_written kolonu + 'empty' status
-- =============================================================================
-- Supabase Dashboard > SQL Editor'da çalıştır. Idempotent'tir.
--
-- Amaç (yol haritası Faz 0 / S0-1):
--   * records_written — botun o koşuda kaynaktan SCRAPE ETTİĞİ kayıt sayısı
--     ([RECORDS] scraped=N satırından; bkz. db_utils.finish_bot_run ve
--     run_all_bots._parse_scraped_records). DB'ye yazılan satır sayısı
--     DEĞİLDİR: zero-cost diff nedeniyle değişmemiş fiyatlar meşru olarak
--     0 yazım üretir, ama scrape 0 ise parser kırıktır.
--   * 'empty' status — bot exit 0 döndü ama 0 kayıt scrape etti. Eskiden bu
--     durum 'success' sayılıyordu ve 4 markanın aylarca sessizce ölü kalmasına
--     yol açtı ("panel yeşil, veri ölü").
-- =============================================================================

ALTER TABLE public.bot_runs
  ADD COLUMN IF NOT EXISTS records_written INTEGER;

COMMENT ON COLUMN public.bot_runs.records_written IS
  'Botun kaynaktan scrape ettiği kayıt sayısı ([RECORDS] scraped=N). DB''ye yazılan satır sayısı değil; 0 = parser kırık/boş kaynak.';

-- Inline CHECK'in otomatik adı bot_runs_status_check'tir; 'empty' eklemek
-- için düşürüp yeniden oluşturuyoruz.
ALTER TABLE public.bot_runs
  DROP CONSTRAINT IF EXISTS bot_runs_status_check;

ALTER TABLE public.bot_runs
  ADD CONSTRAINT bot_runs_status_check
  CHECK (status IN ('success', 'failed', 'timeout', 'skipped', 'empty'));

NOTIFY pgrst, 'reload schema';

-- Doğrulama
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'bot_runs'
ORDER BY ordinal_position;
