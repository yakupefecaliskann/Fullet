-- =============================================================================
-- Marka kullanılabilirliği: hangi markanın ŞU AN haritada gösterilecek verisi var
-- =============================================================================
-- Sorun (14 Ekim 2026 denetimi, §D-1): Shell fiyat kaynağı 9 Eylül'de öldü,
-- fiyatlar 48 saat içinde `unknown`'a döndü ve `fullet-resolve-station-visibility`
-- cron'u fiyatsız kalan 1309 Shell istasyonunu `hidden` yaptı. Zincirin her
-- halkası tasarlandığı gibi çalıştı — ama UYGULAMA BUNU BİLEMİYOR.
--
-- Nedeni mimari: istemci istasyonları yalnızca harita görüş alanı için çekiyor
-- (`get_nearby_stations`, yarıçap sorgusu). Dolayısıyla istemci tarafında
--     "bu BÖLGEDE Shell yok"   ile   "Shell'in HİÇBİR YERDE verisi yok"
-- ayrımı yapılamıyordu. Sonuç iki katmanlı bir kullanıcı zararıydı:
--   1. Marka filtresindeki İLK çip (Shell) boş harita döndürüyordu.
--   2. Boş-durum metni "haritayı kaydırarak farklı bölgede ara" diyerek
--      kullanıcıyı HİÇ VAR OLMAYAN istasyonları aramaya yönlendiriyordu.
--
-- Bu view o ayrımı sunucudan tek istekte veriyor: 6-7 satır, sıcak ~18 ms
-- (soğuk ~510 ms, ölçüldü; fark tamamen önbellek, autovacuum normal çalışıyor).
-- Oturum başına bir kez çekilmesi yeterli.
--
-- `security_invoker = true` (PG15+ özelliği, proje PG 17.6'da): view ÇAĞIRANIN
-- haklarıyla çalışır, yani istasyonlar/fiyatlar üzerindeki RLS aynen uygulanır.
-- anon rolü buradan yalnızca kendi görebildiği istasyonları sayar; `hidden`
-- olanlar kendiliğinden düşer. Aynı işi SECURITY DEFINER bir fonksiyonla
-- yapmak advisor'da kalıcı "anon can execute SECURITY DEFINER" uyarısı
-- bırakırdı — view bu gürültüyü hiç üretmiyor.
--
-- EXISTS koşulu kasıtlı ve fazlalık DEĞİL: `visibility_status='visible'` zaten
-- cron değişmezi gereği "kullanılabilir fiyatı var" anlamına geliyor, ama o
-- değişmeze GÜVENMEK kırılgan olurdu — cron durduğu an view yalan söylemeye
-- başlardı. Doğruluk varsayımla değil inşa yoluyla sağlanıyor.
--
-- Kendi kendini onarır: Shell'e yeni bir fiyat kaynağı tanımlandığı an
-- istasyonlar `visible`'a döner, view onları saymaya başlar ve uygulamadaki
-- çip hiçbir kod değişikliği olmadan yeniden etkinleşir. Hiçbir yerde
-- "Shell" diye sabit kodlanmış bir istisna YOK.
-- =============================================================================

CREATE OR REPLACE VIEW public.marka_kullanilabilirlik
WITH (security_invoker = true) AS
SELECT
  i.marka,
  COUNT(*)::int AS istasyon_sayisi
FROM public.istasyonlar i
WHERE i.aktif IS TRUE
  AND i.visibility_status IN ('visible', 'low_priority')
  AND EXISTS (
    SELECT 1
    FROM public.fiyatlar f
    WHERE f.istasyon_id = i.id
      AND f.price_status IN ('fresh', 'stale')
  )
GROUP BY i.marka;

COMMENT ON VIEW public.marka_kullanilabilirlik IS
  'Markaya göre, anon rolünün haritada görebildiği istasyon sayısı. '
  'Uygulama bunu "bu marka şu anda veri taşıyor mu?" sorusu için kullanır; '
  'boş dönen marka filtresi çipini susturmak yerine dürüstçe etiketler.';

GRANT SELECT ON public.marka_kullanilabilirlik TO anon, authenticated;
