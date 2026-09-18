# Fullet Backend Runbook

Bu dosya canlı Supabase backend'ini güvenli çalıştırmak için kısa operasyon rehberi.

## 1. Migration

Supabase Dashboard > SQL Editor içinde sırayla çalıştır:

```text
database/production_hardening.sql      ← Tablolar, indexler, constraint'ler (fiyat: 5-200 TL)
database/add_status_columns.sql        ← visibility_status + price_status
database/create_postgis_rpc.sql        ← get_nearby_stations v1 + v2 (istasyon+fiyat birleşik)
database/rls_policies.sql              ← RLS politikaları
database/drop_unique_koordinat.sql     ← Eski unique koordinat constraint'i temizle
database/auto_price_staleness.sql      ← pg_cron: otomatik fresh→stale→unknown + token temizleme
database/verify_live_schema.sql        ← Doğrulama sorguları
```

`verify_live_schema.sql` çıktısında ilgili kontroller `true` dönmeli. Özellikle
`istasyonlar_rls_enabled` ve `istasyonlar_anon_policy_filters_active` `true`
olmadan yayın hazır sayılmaz. Eski canlı şemada eksik kolon/RPC varsa:

```text
database/add_status_columns.sql
database/create_postgis_rpc.sql
database/rls_policies.sql
```

`database/live_public_schema_fix.sql` legacy onarım betiğidir; modern
`visibility_status`/`price_status` mimarisini geri alabilecği için normal
release sırasında çalıştırılmaz.


## 2. Health Check

```powershell
python scraper\backend_health_check.py
```

Beklenen final:

```text
[OK] backend health: all checked items passed
```

## 3. Operasyon Raporu

Marka marka aktif istasyon, fiyat ve son güncelleme durumunu görmek için:

```powershell
python scraper\ops_report.py
```

Beklenen final:

```text
[OK] Live data operations report is clean.
```

## 4. Botları Test Et

Veritabanına yazmadan tüm botları dene:

```powershell
$env:FULLET_DRY_RUN='1'
$env:FULLET_ALLOW_DB_WRITE='0'
python scraper\run_all_bots.py
```

## 5. Canlı Veri Yaz

Canlı yazma bilinçli kilitli. Gerçek resmi veriyi yazmak için:

```powershell
$env:FULLET_DRY_RUN='0'
$env:FULLET_ALLOW_DB_WRITE='1'
python scraper\run_all_bots.py --mode prices
```

## 6. Otomasyon Planı

GitHub Actions dosyası: `.github/workflows/otopilot.yml`

- Fiyat botları: günde 4 kez, Türkiye saatiyle yaklaşık `00:20`, `06:20`, `12:20`, `18:20`.
- Haber botu: günde 2 kez, Türkiye saatiyle yaklaşık `08:50`, `20:50`.
- İstasyon envanteri: haftada 1 kez, pazar yaklaşık `04:40`.
- Manuel çalıştırma: GitHub Actions > Fullet Data Automation > Run workflow.

GitHub Actions secrets:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_ANON_KEY
```

`SUPABASE_KEY` eski uyumluluk için fallback olarak kullanılabilir. Bu değer
service-role key ise botlar yazabilir; anon key ise canlı yazma doğrulaması
fail eder. RLS health check için `SUPABASE_ANON_KEY` ayrıca eklenmelidir.

Manuel modlar:

```powershell
python scraper\run_all_bots.py --mode prices
python scraper\run_all_bots.py --mode stations
python scraper\run_all_bots.py --mode news
python scraper\run_all_bots.py --mode all
```

## 6.1 Bakım Araçları (elle çalıştırılır, otomasyonda yoktur)

Bu iki araç zamanlanmış workflow'un parçası **değildir** ve hiçbir yerden
çağrılmaz — kodda referansları olmadığı için "ölü kod" sanılmaya açıktırlar,
silmeyin. İkisi de varsayılan olarak DRY-RUN'dır; yazmak için
`FULLET_ALLOW_DB_WRITE=1` gerekir.

```powershell
python scraper\purge_inactive_stations.py   # 30+ gündür dokunulmamış pasif istasyon kayıtlarını siler
python scraper\merge_duplicate_stations.py  # aynı istasyonun yinelenen kayıtlarını birleştirir
```

`purge_inactive_stations.py` neden gerekli: envanter botu doğrulayamadığı
istasyonu `aktif=False` ile yazar; kayıt bir daha hiç doğrulanmazsa sonsuza
kadar birikir. 30 gün eşiği, haftalık envanter koşusunun dört turudur.

## 7. Kaynak Kuralı

Fullet canlıya sahte fiyat veya tahmini istasyon basmaz. Fiyatlar resmi
kaynaklardan, koordinatlar resmi istasyon envanteri/locator kaynaklarından
gelmelidir.

## 7.1 Ölen Bir Kaynak — `scraper/known_outages.py`

Bir kaynak sitesi kalıcı olarak kapandığında (Shell `/pompatest/`, 9 Eyl 2026)
kodda düzeltilecek bir şey yoktur, ama düzeltilmeden bırakmak da olmaz: bot her
koşuda başarısız olur ve **pipeline kalıcı kırmızıya döner**. Kırmızı sabitlenince
sinyal olmaktan çıkar — başka bir bot kırılsa kimse fark etmez (bkz.
`docs/KOD_DENETIM_ARSIVI.md` Bölüm E).

Çözüm, botu "tolere edilenler" listesine atmak **değildir** (o liste tam bu
yüzden boşaltıldı). Bunun yerine `scraper/known_outages.py`'ye bir kayıt eklenir:

```python
KnownOutage(
    bot="ornek_bot.py", brand="Örnek",
    url="https://...", reason="Kaynak neden öldü, hangi alternatifler elendi",
    since=date(2026, 9, 9), review_by=date(2026, 10, 31),
)
```

Kaydın üç sınırı vardır ve üçü de kasıtlıdır:

1. Yalnızca botun **çalışma anında doğruladığı** ölü kaynağı (`EXIT_SOURCE_GONE`)
   susturur. Parser kırılıp 0 kayıt dönerse pipeline yine kırmızıdır.
2. `review_by` geçince susturmayı bırakır; sağlık kontrolü yeniden kırmızı olur.
3. Bot iyileşirse sağlık kontrolü kırmızıya döner ve **kaydın silinmesini** ister.

Bot rotasyondan ÇIKARILMAZ: rotasyonda kaldığı sürece her koşuda kaynağı yoklar,
yani "kaynak geri döndü mü?" tespiti de sürer. Kaynak dönerse
`database/auto_price_staleness.sql` JOB 5b gizlenen istasyonları bir saat içinde
kendiliğinden `visible` yapar.

## 7.2 Dashboard "Database Webhooks" kullanmayın

18 Eyl 2026'da Dashboard arayüzüyle kurulmuş tek bir webhook kaldırıldı ve
veritabanının **%70'ini** geri kazandırdı (336 MB → 101 MB). Arayüzün ürettiği
tetikleyicinin üç kalıcı sorunu var:

1. **`Authorization` başlığına `service_role` anahtarını DÜZ METİN gömüyor.**
   Anahtar `pg_get_triggerdef` ile okunabilir ve her `pg_dump`'a girer.
2. **Her çağrıyı `supabase_functions.hooks`'a yazıyor ve kimse temizlemiyor.**
   330.919 satır / 44 MB birikmişti.
3. **`FOR EACH ROW` kuruluyor.** Toplu yazan bir bota bağlanırsa tek koşuda
   binlerce HTTP isteği doğurur (bizde tek zam = 9.028 istek), `net._http_response`
   da onunla birlikte şişer (191 MB).

Bir şeyin DB değişikliğine tepki vermesi gerekiyorsa: `FOR EACH STATEMENT`
kullanın ya da işi kazıma sonrasında uygulama katmanında yapın; sırrı Vault'ta
tutun (`supabase_vault` kurulu). Denetimde bakılacaklar:

```sql
-- Sır sızdıran tetikleyici var mı? (0 olmalı)
SELECT count(*) FROM pg_trigger
WHERE NOT tgisinternal AND pg_get_triggerdef(oid) ~ 'eyJhbGciOi';

-- Sessizce büyüyen altyapı tabloları + katman sınırı (ücretsiz: 500 MB)
SELECT pg_size_pretty(pg_database_size(current_database())) AS db,
       pg_size_pretty(pg_total_relation_size('supabase_functions.hooks')) AS hooks,
       pg_size_pretty(pg_total_relation_size('net._http_response')) AS pg_net;
```

## 8. Admin Panel ve Observability

Admin panel için önce Supabase SQL Editor içinde çalıştır:

```text
database/admin_observability.sql
```

Ardından kendi giriş e-postanı admin listesine ekle:

```sql
INSERT INTO public.admin_emails (email)
VALUES ('senin-emailin@example.com')
ON CONFLICT DO NOTHING;
```

Panel klasörü:

```text
admin_panel
```

Lokal çalışma:

```powershell
cd admin_panel
npm install
npm run dev
```

Bot çalışmaları `bot_runs`, açık sorunlar `system_alerts`, anonim cihaz
heartbeat kayıtları `app_heartbeats` tablosundan takip edilir.

## 9. Kabul Edilmiş Güvenlik Uyarısı — `public.spatial_ref_sys`

*(Son inceleme: 2026-05-09. Eskiden `docs/SUPABASE_SECURITY_ADVISOR_NOTES.md`.)*

Supabase Security Advisor, `public.spatial_ref_sys` için `RLS Disabled in Public`
uyarısı gösterebilir. Bu tablo PostGIS eklentisi tarafından oluşturulur ve
koordinat sistemi meta verisi tutar — Fullet'in kullanıcı, istasyon, fiyat, admin
veya token verisi **değildir**. Uyarı, Data API'ye açık tüm public şema
tablolarında RLS istenmesi genel kuralından geliyor.

Bu projede SQL Editor'den RLS açmayı denemek şu hatayla düşer:

```text
ERROR: 42501: must be owner of table spatial_ref_sys
```

Yani tablo PostGIS eklenti sahibine ait. **Bu uyarıyı gidermek için canlıda
`DROP EXTENSION postgis CASCADE` ÇALIŞTIRMA** — PostGIS, istasyon konum kolonunu
ve yakındaki-istasyon RPC'lerini besliyor.

Güvenli teşhis:

```text
database/postgis_spatial_ref_sys_owner_check.sql
```

Uzun vadeli kalıcı çözüm:

- Önce veritabanı yedeği al.
- PostGIS'i `extensions`/`gis` gibi public olmayan bir şemaya taşı/yeniden kur
  (Supabase'in PostGIS sorun giderme rehberine göre).
- PostGIS 2.3+ normalde yeniden konumlandırılabilir olmadığı için Supabase ya
  yedek/drop/recreate/restore akışını ya da taşımayı Supabase Support'un
  yapmasını öneriyor.

**Yayın kararı:** Bu uyarı Fullet'in yayınını engellemez. Planlı bir veritabanı
bakım penceresine kadar *kabul edilmiş altyapı uyarısı* olarak kalır.
