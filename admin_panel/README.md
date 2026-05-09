# Fullet Admin Panel

Web tabanli operasyon paneli. Bot durumu, veri tazeligi, haber tazeligi,
anonim aktif cihaz metrikleri ve sistem alarmlarini gosterir.

Canli panel: https://yakupefecaliskann.github.io/Fullet/
Gizlilik politikasi: https://yakupefecaliskann.github.io/Fullet/privacy.html

## Kurulum

1. Supabase SQL Editor icinde calistir:

```text
database/admin_observability.sql
```

2. Admin mailini ekle:

```sql
INSERT INTO public.admin_emails (email)
VALUES ('senin-emailin@example.com')
ON CONFLICT DO NOTHING;
```

3. `admin_panel/.env` dosyasi olustur:

```text
VITE_SUPABASE_URL=https://xhkvlwecsacfjpbtyqcc.supabase.co
VITE_SUPABASE_ANON_KEY=...
```

4. Lokal calistir:

```powershell
npm install
npm run dev
```

Supabase Authentication > URL Configuration icinde panelin domainini
`Redirect URLs` listesine ekle. Lokal test icin Vite'in verdigi
`http://localhost:5173` adresi de eklenebilir.

## Build

```powershell
npm run build
```

`dist` klasoru statik olarak GitHub Pages, Netlify veya Vercel uzerinde
ucretsiz yayinlanabilir.

GitHub Pages icin hazir workflow:

```text
.github/workflows/admin-panel-pages.yml
```

GitHub repo > Settings > Pages kisminda source olarak `GitHub Actions` sec.
Sonra Actions > Fullet Admin Panel > Run workflow calistir.

## Guvenlik

- Service-role key bu panele konulmaz.
- Panel sadece Supabase anon key kullanir.
- Admin verileri RLS ile korunur.
- `app_heartbeats` tablosuna uygulama sadece RPC uzerinden anonim heartbeat yazar.
