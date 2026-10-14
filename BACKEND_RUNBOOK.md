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

### Hangi sayıya güvenilir: `Shown` vs `Active`

Tablonun **ilk** sütunu `Shown` ve bu kasıtlı — raporu okuyanın güvenmesi
gereken sayı budur:

| Sütun | Ne söyler |
|---|---|
| **`Shown`** | **Kullanıcının gerçekten görebildiği** istasyon sayısı (`visibility_status` RLS allowlist'inde) |
| `Active` | Veritabanındaki `aktif=true` satır sayısı |

İkisi ayrışabilir ve ayrıştığında alt tarafta şu satır çıkar:

```text
  -> 1309 aktif istasyon KULLANICIYA GÖRÜNMÜYOR (envanterin %18,7'i; ...)
```

**Neden bu ayrım var:** 14 Ekim 2026 denetimine kadar rapor yalnızca `Active`
basıyordu. Shell kaynağı 9 Eylül'de ölünce cron 1309 istasyonu `hidden` yaptı,
ama rapor 33 gün boyunca `Total active stations: 6992` demeye devam etti — yani
ürünün beşte biri karanlıkken bakılan rakam sakin görünüyordu
(bkz. `docs/KOD_DENETIM_ARSIVI.md` §F-Y1).

Bir markanın `Shown` değeri **0** olup `Active` değeri pozitifse uyarı açılır.
**Kısmi** fark uyarı üretmez (olağan dalgalanma; her koşuda basmak sahte alarm
gürültüsü olurdu) — bu durumda sayıya `Shown` sütunundan bakın.

> `USER_VISIBLE_STATUSES` (ops_report.py) `rls_policies.sql`'deki
> "public read istasyonlar" allowlist'iyle **birebir aynı** olmak zorundadır.
> RLS'e yeni bir durum değeri eklenirse buraya da eklenmeli; `test_ops_report.py`
> sapmayı yakalar.

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

---

## 10. Açık Elle İşler — 14 Ekim 2026 Denetimi

**Toplam iki iş kaldı (10.1 ve 10.2).** İkisi de kod tarafında kapatıldı ama
üretimde elle uygulanması gerekiyor: Claude Code'un auto-mode classifier'ı
üretimde yıkıcı DDL'i (DROP) engelliyor, Supabase MCP'sinde de
`delete_edge_function` yok. Yani bunlar bilinçli olarak insan onayına bırakılmış
eylemler, eksik kalmış işler değil. Ayrıntılar: `docs/KOD_DENETIM_ARSIVI.md` §F.

İkisi de **acil değil**: ne kullanıcıyı ne de veri akışını etkiliyorlar.
Birikmiş teknik borcun kapanışı.

> §10.3 (Shell kaynak kararı) **14 Ekim'de ele alındı ve son tarih 15 Aralık'a
> çekildi** — artık 31 Ekim'de kendiliğinden kırmızıya düşme riski YOK.
> Yine de bir ürün kararı bekliyor; aşağıya bakın.

### 10.1 Ölü şemayı düşür (`user_profiles` / `user_favorites`)

Migration dosyası hazır ve gerekçesi içinde:
`supabase/migrations/20261014120100_olu_kullanici_semasi_kaldirildi.sql`

Supabase Dashboard → SQL Editor'da:

```sql
DROP TABLE IF EXISTS public.user_favorites;
DROP TABLE IF EXISTS public.user_profiles;
```

**Sıra önemli** (`user_favorites.user_id → user_profiles.id` FK'si var) ve
`CASCADE` kullanılmamalı. Düşürme öncesi doğrulanmıştı: her ikisi de 0 satır,
depoda tek kod referansı yok. Yedek bilinçli olarak alınmadı — 0 satırlık yedek
tablo veri taşımaz ama RLS'siz kaldığı için linter'da kalıcı ERROR üretir.

### 10.2 Yetim Edge Function'ı sil (`fiyat-push`)

Fonksiyon üretimde hâlâ `ACTIVE` (v4) ama kesin ölü: düşürülmüş `push_tokens`
tablosunu okuyor, onu çağıran trigger kaldırıldı, yalnızca Expo token'larına
gönderiyor (proje Firebase'de). Çağrılsa anında patlar.

```powershell
npx supabase login
npx supabase functions delete fiyat-push --project-ref xhkvlwecsacfjpbtyqcc
```

Ya da Dashboard → Edge Functions → `fiyat-push` → Delete.

Kaynağı kaybolmuyor: commit `224d200` içinde duruyor
(`supabase/functions/fiyat-push/index.ts`, 3 Ağustos 2026'da depodan silinmişti).

### 10.3 Shell fiyat kaynağı kararı — ✅ ELE ALINDI, yeni tarih 15 ARALIK 2026

**14 Ekim 2026'da seçenek (d) uygulandı: kayıt kanıta dayalı olarak uzatıldı.**
`scraper/known_outages.py` içindeki Shell kaydının `review_by` tarihi
**2026-10-31 → 2026-12-15**. Yani 31 Ekim'de kendiliğinden kırmızıya düşme
riski **ortadan kalktı**.

Uzatma körü körüne yapılmadı; kaynak önce yeniden tarandı (14 Eki 2026):

| Kontrol | Sonuç |
|---|---|
| `turkiyeshell.com/pompatest/History.aspx` | HTTP 404 |
| `turkiyeshell.com/pompatest/` | HTTP 404 |
| `shell.com.tr/sitemap.xml` içinde fiyat sayfası | **YOK** (yalnızca `how-shell-price` açıklama sayfası — JS iskeleti, tek fiyat sayısı yok — ve Shell Recharge EV tarife sayfası) |
| Ana sayfadaki "akaryakıt fiyatları" ifadesi | SEO meta metni; href'lerde fiyat bağlantısı yok |
| `find.shell.com` (daha önce elendi) | TR için `fuel_pricing.status='unavailable'` |

**Neden 15 Aralık (~9 hafta):** Bu tarihin işi kaynak tespiti DEĞİL — bot
rotasyonda kaldığı sürece her koşuda kaynağı yokluyor ve dönerse sağlık
kontrolü kaydın silinmesini zaten ister (§7.1). Tarihin tek işi **insan
kararını zorlamak.** Haftalık yoklama boşa iş olurdu; 6 ay ise
`known_outages.py`'nin en başında uyardığı "kalıcı göz bağı" hâline gelirdi.
Yıl sonu tatillerinden önceye denk gelsin diye 15 Aralık.

> **ÜÇÜNCÜ BİR UZATMA YAPMAYIN.** İki kez uzatılmış bir kayıt, kararın
> verilmediğini söyler. O noktada doğru hamle tarihi tekrar ötelemek değil,
> aşağıdaki seçeneklerden birini kalıcı olarak seçmektir.

Hâlâ bekleyen ürün kararı ve bedelleri:

| Seçenek | Bedel |
|---|---|
| **(a)** 3. taraf toplayıcı | Provenance düşüşü + ToS riski |
| **(b)** Shell'i marka listesinden ve envanterden çıkar | 1309 istasyon kalıcı kaybı |
| **(c)** İstasyonları fiyatsız/konum amaçlı göster | Fiyat vaadi zayıflar, konum değeri kalır |
| **(d)** ~~Arıza kaydını bilinçli uzat~~ | ✅ 14 Eki 2026'da bir kez kullanıldı |

Hangisi seçilirse seçilsin, kararın gerekçesi `known_outages.py`'deki `reason`
alanına yazılmalı — altı hafta sonra o satırı okuyan kişi aynı araştırmayı
baştan yapmasın.

> **Not:** Shell'e yeni bir kaynak tanımlandığı an uygulama tarafında hiçbir
> şey yapmak gerekmiyor. İstasyonlar `visible`'a döner, `marka_kullanilabilirlik`
> view'i onları saymaya başlar ve marka filtresindeki çip kendiliğinden
> etkinleşir. Hiçbir yerde "Shell" sabit kodlu istisna bırakılmadı.
