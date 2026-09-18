-- =============================================================================
-- Fullet: "Fiyat Push Tetikleyici" kaldırılıyor + biriken çöp temizleniyor
-- =============================================================================
-- Uygulandı: 18 Eylül 2026. Idempotent'tir.
-- Denetim kaydı: docs/KOD_DENETIM_ARSIVI.md Bölüm E (E-G1, E-G2).
--
-- --- NE VARDI -------------------------------------------------------------
--
--   CREATE TRIGGER "Fiyat Push Tetikleyici"
--     AFTER INSERT ON public.fiyat_gecmisi
--     FOR EACH ROW
--     EXECUTE FUNCTION supabase_functions.http_request(
--       'https://<proje>.supabase.co/functions/v1/fiyat-push',
--       'POST',
--       '{"Content-type":"application/json","Authorization":"Bearer <SERVICE_ROLE_JWT>"}',
--       '{}', '5000');
--
-- Supabase Dashboard'un "Database Webhooks" arayüzüyle kurulmuştu.
--
-- --- NEDEN KALDIRILIYOR (beşi de canlıda doğrulandı) ----------------------
--
-- 1. HEDEF TABLO YOK. Edge function `public.push_tokens`'tan okuyor; o tablo
--    bu projede HİÇ oluşturulmamış. Her çağrı `tokenError` alıp
--    "OK (No target devices)" dönüyor. Kanal hiçbir zaman çalışmadı.
--
-- 2. YANLIŞ PUSH SAĞLAYICISI. Edge function `ExponentPushToken` bekliyor
--    (Expo / React Native). Fullet Flutter + Firebase; `fullet_flutter/lib`
--    altında ne `firebase_messaging` ne de herhangi bir token kaydı var.
--    Tablo oluşturulsa bile bu kod bu uygulamaya bildirim gönderemezdi.
--
-- 3. FOR EACH ROW — YAYILMA FELAKETİ. Tetikleyici fiyat GEÇMİŞİ satırı başına
--    ateşleniyor ve edge function her çağrıda TEK bir istasyonun metnini
--    üretip TÜM cihazlara yolluyor. 16 Eyl 2026 gecesi tek bir ulusal zam
--    9.028 geçmiş satırı yazdı → 9.028 ayrı HTTP isteği. Kanal çalışsaydı bu,
--    kayıtlı her cihaza 10 dakikada 9.028 bildirim demekti. Bu bir maliyet
--    sorunu değil, kullanıcıyı kaybettirecek bir arıza olurdu.
--
-- 4. DÜZ METİN service_role JWT. Tetikleyici tanımı, RLS'i tamamen aşan
--    service_role anahtarını açık metin taşıyordu (exp 2036). Tanım
--    `pg_get_triggerdef` ile okunabiliyor ve her `pg_dump`'a giriyordu.
--    (Doğrulandı: anahtar public depoya VEYA git geçmişine SIZMAMIŞ; admin
--    panel bundle'ındaki JWT `anon` anahtarıdır, o herkese açık olmalıdır.)
--
-- 5. ÖLÇÜLEN MALİYET: `net._http_response` 191 MB + `supabase_functions.hooks`
--    330.919 satır / 44 MB = 336 MB'lık veritabanının ~%70'i. İkisi de
--    yalnızca bu tetikleyici yüzünden birikti ve hiçbir şey onları
--    temizlemiyordu.
--
-- --- PUSH GERÇEKTEN İSTENİRSE NASIL KURULMALI ----------------------------
--
-- Bu tetikleyiciyi geri koymayın. Doğrusu:
--   a) Firebase Cloud Messaging (uygulamanın gerçekten kullandığı sağlayıcı),
--      Expo değil. Cihaz token'ları için bir `push_tokens` tablosu + RLS.
--   b) FOR EACH STATEMENT (ya da tamamen uygulama katmanında, kazıma
--      sonrasında) — satır başına DEĞİL. Bir zam TEK bildirim üretmeli;
--      kullanıcının garajındaki markaya/yakıta göre süzülmeli.
--   c) Sır Vault'ta (`supabase_vault` bu projede KURULU), tetikleyici
--      tanımında değil.
--   d) Opt-in: kullanıcı istemeden bildirim gönderilmemeli.
-- =============================================================================

-- 1) Tetikleyiciyi düşür. Sır da tanımla birlikte gider.
DROP TRIGGER IF EXISTS "Fiyat Push Tetikleyici" ON public.fiyat_gecmisi;

-- 2) Biriken çöpü temizle.
--    DİKKAT: ikisi de TRUNCATE ile değil, HEDEFLİ predicate ile siliniyor.
--    `net._http_response` için kullanılan koşul pg_net'in KENDİ kuralıdır
--    (`pg_net.ttl` = 6 saat); worker yalnızca yeni istek işlerken temizlik
--    yaptığı için 16 Eyl'den beri boşta kalmıştı. `hooks` için koşul, artık
--    var olmayan tek hook'un adıdır — tabloda başka hook_name yoktu.
DELETE FROM net._http_response
WHERE created < now() - interval '6 hours';

DELETE FROM supabase_functions.hooks
WHERE hook_name = 'Fiyat Push Tetikleyici';

-- 3) Alanı işletim sistemine geri ver. VACUUM transaction bloğunda çalışmaz —
--    bu iki satırı SQL Editor'da tek tek çalıştır.
VACUUM FULL net._http_response;
VACUUM FULL supabase_functions.hooks;

-- --- 18 EYLÜL 2026'DA ÖLÇÜLEN SONUÇ --------------------------------------
--   net._http_response        191 MB  ->  32 kB   (9.028 satır -> 0)
--   supabase_functions.hooks   44 MB  ->  32 kB   (330.919 satır -> 0)
--   VERİTABANI TOPLAM         336 MB  -> 101 MB   (%70 geri kazanıldı)
--   JWT taşıyan tetikleyici        1  ->  0
--
--   İş verisi DEĞİŞMEDİ: fiyat_gecmisi 313.723, fiyatlar 17.476,
--   aktif istasyon 6.960. `trigger_fiyat_guncelleme` (log_fiyat_degisimi) ve
--   `trigger_set_konum` etkin kaldı — fiyat geçmişi zinciri sağlam.
--   Supabase ücretsiz katman sınırı 500 MB: önce %67 doluydu, şimdi %20.
-- -------------------------------------------------------------------------

-- 2) Doğrulama: fiyat_gecmisi üzerinde webhook tetikleyicisi KALMAMALI.
--    `trigger_fiyat_guncelleme` (fiyatlar üzerinde, log_fiyat_degisimi) ve
--    `trigger_set_konum` (istasyonlar üzerinde) ÇEKİRDEKTİR — onlara dokunulmadı.
SELECT c.relname AS tablo, t.tgname AS kalan_trigger, n2.nspname AS fonksiyon_semasi
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_proc p ON p.oid = t.tgfoid
JOIN pg_namespace n2 ON n2.oid = p.pronamespace
WHERE NOT t.tgisinternal AND n.nspname = 'public'
ORDER BY 1, 2;

-- 3) Sızıntı denetimi: hiçbir tetikleyici tanımında JWT kalmamalı.
SELECT count(*) AS tanimda_kalan_jwt
FROM pg_trigger t
WHERE NOT t.tgisinternal
  AND pg_get_triggerdef(t.oid) ~ 'eyJhbGciOi';
