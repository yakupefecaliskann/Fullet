# database/ — Şema Değişiklik Disiplini

Bu klasördeki `.sql` dosyaları Fullet'in Supabase (Postgres) şemasının **fiili kaynağı**dır — bugüne kadar `supabase/migrations/` neredeyse hiç güncellenmediği için (tek, eski bir dosya) gerçek şema geçmişi burada, elle Supabase SQL Editor'da çalıştırılan script'lerde yaşadı. Bu durum versiyon kontrolü ve tekrarlanabilirlik açısından kırılgan; aşağıdaki kural bunu düzeltmenin başlangıcı.

## Kural

Yeni bir şema değişikliği (tablo, kolon, RLS, RPC, index) yapıldığında:

1. Önce burada (`database/`) idempotent bir `.sql` dosyası yazılır (`CREATE TABLE IF NOT EXISTS`, `CREATE OR REPLACE FUNCTION`, `DROP POLICY IF EXISTS` + `CREATE POLICY` gibi — dosya defalarca güvenle çalıştırılabilmeli).
2. Aynı içerik, zaman damgalı bir kopya olarak `supabase/migrations/YYYYMMDDHHMMSS_kisa_aciklama.sql` altına da eklenir.
3. Dosya Supabase Dashboard → SQL Editor'da çalıştırılır (bu adım kullanıcı eylemidir, CI/otomatik değildir).
4. Şema doğrulaması gerekiyorsa `verify_live_schema.sql`'e ilgili kontrol satırı eklenir.

Bu iki dosyanın (`database/` ve `supabase/migrations/`) içeriği **birbirinin aynısı** olmalı — `database/` okunabilir/organize edilmiş kaynak, `supabase/migrations/` ise zaman sıralı, değiştirilemez geçmiş.

## Bilinen istisnalar / uyarılar

- `production_hardening.sql` ve `live_public_schema_fix.sql` kendi başlıklarında "normal release sırasında production'da çalıştırma" uyarısı taşıyor — geçmişte bir kez yanlışlıkla çalıştırılıp `visibility_status` mimarisini bozmuş olabilir. Bu iki dosyayı çalıştırmadan önce içeriğini dikkatlice oku.
- `verify_live_schema.sql` bir doğrulama script'idir, şema değiştirmez — `supabase/migrations/`'a kopyalanmaz.
- Bu kural geriye dönük olarak klasördeki 20+ eski dosyayı migrations'a taşımayı zorunlu kılmıyor; yalnızca **yeni** değişiklikler için geçerli. Geçmiş dosyalar zamanla, dokunuldukça migrations'a eklenebilir.
