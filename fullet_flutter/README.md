# Fullet Flutter

Fullet is a Flutter fuel-price map app backed by Supabase.

## Run Checks

```powershell
flutter analyze
flutter test
flutter build apk --debug
flutter build appbundle --release
```

## Backend

Run the idempotent SQL hardening scripts in Supabase SQL Editor before production use:

```text
../database/production_hardening.sql
../database/rls_policies.sql
../database/verify_live_schema.sql
```

Detailed backend operations live here:

```text
../BACKEND_RUNBOOK.md
```

## Scrapers

Run a no-write verification first:

```powershell
$env:FULLET_DRY_RUN='1'
python ..\scraper\run_all_bots.py
```

Production writes require Supabase secrets in `../scraper/.env` or GitHub Actions secrets.

## Backend Health Check

```powershell
python ..\scraper\backend_health_check.py
```
