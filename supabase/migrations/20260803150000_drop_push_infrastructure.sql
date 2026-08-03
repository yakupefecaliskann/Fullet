-- =============================================================================
-- Push altyapısını kaldır (yol haritası madde 22 + 23)
-- =============================================================================
-- Uçtan uca kopuktu ve hiçbir zaman çalışmadı:
--   * `push_tokens` tablosunda 0 satır vardı.
--   * Flutter uygulaması `firebase_messaging` kullanmıyor ve tabloya hiç
--     yazmıyordu — depoda tek bir INSERT yoktu.
--   * `fiyat-push` Edge Function yalnızca Expo token'larına gönderiyordu;
--     FCM token'ları sayılıp "pendingFcm" olarak raporlanıyor, gönderilmiyordu.
--
-- Kullanıcı kararı (3 Ağustos 2026): tamamlamak yerine KALDIR.
--
-- KALAN (kaldırılmadı): cihaz üstü YEREL bildirimler —
-- `NotificationService` (yakıt hatırlatıcısı, garaj hatırlatıcısı, fiyat
-- alarmı). Onlar çalışıyor ve push altyapısına bağlı değil.
--
-- Birlikte kaldırılanlar: `fullet-cleanup-push-tokens` pg_cron job'u
-- (bkz. database/auto_price_staleness.sql), `supabase/functions/fiyat-push/`,
-- `scraper/summary_push.py`, `database_writes.send_summary_push`.
-- =============================================================================

DROP TABLE IF EXISTS public.push_tokens;

-- `price_alerts.push_token`: fiyat alarmı bildirimi cihazda YEREL olarak
-- gösteriliyor (price_alert_service.dart -> NotificationService), uzak push
-- token'ına ihtiyaç yok. Flutter kodunda tek bir okuma/yazma referansı yok.
ALTER TABLE public.price_alerts DROP COLUMN IF EXISTS push_token;
