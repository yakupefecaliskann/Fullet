# Fullet Backend Runbook

Bu dosya canlı Supabase backend'ini güvenli çalıştırmak için kısa operasyon rehberi.

## 1. Migration

Supabase Dashboard > SQL Editor içinde sırayla çalıştır:

```text
database/production_hardening.sql
database/rls_policies.sql
database/drop_unique_koordinat.sql
database/verify_live_schema.sql
```

`verify_live_schema.sql` çıktısında ilgili kontroller `true` dönmeli. Özellikle
`istasyonlar_rls_enabled` ve `istasyonlar_anon_policy_filters_active` `true`
olmadan yayın hazır sayılmaz. Eski canlı şemada eksik kolon/RPC varsa:

```text
database/live_public_schema_fix.sql
```

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

Manuel modlar:

```powershell
python scraper\run_all_bots.py --mode prices
python scraper\run_all_bots.py --mode stations
python scraper\run_all_bots.py --mode news
python scraper\run_all_bots.py --mode all
```

## 7. Kaynak Kuralı

Fullet canlıya sahte fiyat veya tahmini istasyon basmaz. Fiyatlar resmi
kaynaklardan, koordinatlar resmi istasyon envanteri/locator kaynaklarından
gelmelidir.
