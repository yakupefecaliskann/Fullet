# database/ — Şema Değişiklik Disiplini

> **Güncellendi: 3 Ağustos 2026 (yol haritası madde 24).** Tek doğruluk kaynağı
> artık `supabase/migrations/`. Bu klasör onun *ikizi* değil, tamamlayıcısıdır.

## Doğruluk kaynağı

**`supabase/migrations/` = şemanın tek doğruluk kaynağıdır.** Zaman sıralı,
değiştirilemez geçmiş. Yeni her şema değişikliği (tablo, kolon, RLS, RPC,
index, pg_cron job) buraya `YYYYMMDDHHMMSS_kisa_aciklama.sql` olarak yazılır.

**`database/` = iki tür dosya barındırır**, ikisi de doğruluk kaynağı DEĞİLDİR:

1. **Tek seferlik onarım script'leri** — `repair_composite_province_values.sql`,
   `reset_hidden_regional_stations.sql` gibi. Bir kez çalıştırılır, tarihsel
   kayıt olarak kalır.
2. **Doğrulama script'leri** — `verify_live_schema.sql`. Şema değiştirmez.

Tek istisna `auto_price_staleness.sql`: pg_cron job'ları migration'la değil
elle kurulduğu için okunabilir kaynak burada tutuluyor. **Bu dosya canlıyla
BİREBİR aynı olmak zorundadır** — birini değiştiren diğerini de değiştirmeli.

## Neden değişti — gerçek bir drift yaşandı

Eski kural "`database/` ve `supabase/migrations/` içeriği birbirinin aynısı
olmalı" diyordu. Bu kural pratikte tutmadı ve **3 Ağustos 2026'da canlı bir
tuzağa dönüştü**: Faz 1'de `son_dogrulama` kolonu eklenip pg_cron JOB 1/2
canlıda `COALESCE(son_dogrulama, son_guncelleme)`ye çevrilmişti, ama
`auto_price_staleness.sql` hâlâ `son_guncelleme` diyordu. Dosyayı iyi niyetle
yeniden çalıştıran biri Faz 1'in en değerli düzeltmesini geri alır ve
fiyatların `fresh → stale → fresh` salınımını geri getirirdi.

İki kaynağı senkron tutmak insan disiplinine bağlıydı; disiplin tutmadı.
Artık tek kaynak var.

## Bayat dosya uyarıları

Aşağıdaki dosyalar hâlâ **kaldırılmış** yapıları oluşturuyor ve başlıklarına
uyarı bandı eklendi. Çalıştırılırlarsa ölü yapıları geri getirirler:

| Dosya | Sorun |
|---|---|
| `production_hardening.sql` | `push_tokens` tablosunu oluşturur (tablo düşürüldü) |
| `live_public_schema_fix.sql` | aynı |
| `rls_policies.sql` | aynı |
| `add_price_verification.sql` | `push_tokens` temizlik job'u içerir |
| `supabase/migrations/20260708120100_*` | `get_nearby_stations`i 4 argümanlı tanımlar; bir sonraki migration onu ezer. Tek başına çalıştırılırsa iki overload kalır, PostgREST çağrıyı çözemez |

`production_hardening.sql` ve `live_public_schema_fix.sql` ayrıca kendi
başlıklarında "normal release sırasında production'da çalıştırma" uyarısı
taşıyor — geçmişte bir kez yanlışlıkla çalıştırılıp `visibility_status`
mimarisini bozmuş olabilir.

## Kaldırılmış yapılar (3 Ağustos 2026)

* `push_tokens` tablosu, `price_alerts.push_token` kolonu, `fiyat-push` Edge
  Function, `fullet-cleanup-push-tokens` pg_cron job'u — push altyapısı uçtan
  uca kopuktu ve kaldırıldı (madde 22/23). Bkz.
  `supabase/migrations/20260803150000_drop_push_infrastructure.sql`.
  **Cihaz üstü yerel bildirimler kaldırılmadı**, onlar çalışıyor.
