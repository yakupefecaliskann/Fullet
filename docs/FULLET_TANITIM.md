# Fullet — Teknik Tanıtım (Ekip Dokümanı)

> Konum tabanlı akaryakıt fiyatı haritası. Yakındaki istasyonların fiyatını gösterir,
> aracının tüketim + mesafe maliyetini de hesaba katarak "en mantıklı istasyon"u önerir.
> **Sürüm:** `1.0.2+4` · **Platform:** Flutter (Android odaklı)

Bu doküman, "Fullet teknik olarak neyi nasıl yapıyor?" sorularına tek elden, kodla
doğrulanmış cevap verir. Tüm iddialar kaynak kod incelemesinden gelir; henüz yarım olan
özellikler açıkça öyle işaretlenmiştir.

---

## 1. Bir Cümlede Fullet

Supabase (Postgres + PostGIS) backend'e Google Maps ile bağlanan, konum tabanlı bir
Flutter yakıt fiyatı haritası. Fiyatlar hazır bir API'den değil, **kendi Python scraper
botlarımız** tarafından günde 4 kez toplanır. Çekirdek ayırt edici özellik: sadece litre
fiyatını değil, aracın tüketimini ve istasyona gitme maliyetini de puanlayan **"akıllı
istasyon"** önerisi.

---

## 2. Sistem Mimarisi

Dört bileşenli monorepo:

| Klasör | Bileşen | Teknoloji |
|--------|---------|-----------|
| `fullet_flutter/` | Mobil uygulama | Flutter / Dart |
| `scraper/` | Fiyat/istasyon toplama botları | Python |
| `admin_panel/` | Operasyon paneli | React 19 + Vite 7 |
| `supabase/` + `database/` | Backend şema & fonksiyonlar | Postgres, PostGIS, RLS, pg_cron, Edge Functions (Deno) |

Veri akışı:

```
  Kaynaklar (marka API / web siteleri)
          │  scraping / API
          ▼
  Python botlar  ──(GitHub Actions cron, günde 4×)──┐
          │  service-role key ile yazma             │
          ▼                                          │
  Supabase Postgres + PostGIS  ◀────────────────────┘
     │ (public read, RLS)          ▲ pg_cron (eskitme, temizlik)
     │                             │ Edge Function (fiyat-push → Expo)
     ├───────────────┬─────────────┘
     ▼               ▼
  Flutter app     Admin panel (React, anon key)
  (Google Maps)   (bot sağlığı / metrikler)
```

---

## 3. Fiyat Verisi Nasıl Toplanıyor?

**Tek bir API yok.** Her marka için ayrı bir bot, markanın sunduğu en güvenilir kaynağı
kullanır. Kaynak beyaz listesi `scraper/config.py` içinde tanımlıdır.

| Marka | Kaynak | Yöntem |
|-------|--------|--------|
| Opet | `api.opet.com.tr/api/fuelprices/allprices` | JSON API |
| TotalEnergies | `apimobile.guzelenerji.com.tr/exapi/fuel_prices` | JSON API |
| Petrol Ofisi | `petrolofisi.com.tr/akaryakit-fiyatlari` | HTML scraping |
| BP | `petrolofisi.com.tr/.../bp` | HTML scraping |
| Aytemiz | `aytemiz.com.tr/akaryakit-fiyatlari` | HTML scraping |
| Türkiye Petrolleri | `tppd.com.tr/akaryakit-fiyatlari` | HTML scraping |
| **Shell** | `turkiyeshell.com/pompatest/History.aspx` | **Playwright (headless Chromium)** |

### Shell neden özel?
Shell toplu bir fiyat API'si sunmadığı için, DevExpress tabanlı "pompa test" sayfasını
**headless Chromium (Playwright)** ile il/ilçe dropdown'larını tek tek gezerek okuruz
(`scraper/shell_bot.py`). Site eşzamanlı bağlantıyı engellediğinden akış sıralıdır:

- Koşu başına en fazla **150 il/ilçe** hedefi (`DEFAULT_MAX_TARGETS_PER_RUN`)
- **İstanbul, Ankara, İzmir** her koşuda öncelikli
- Kalan hedefler 6 saatlik pencerelerde **rotasyonla** dönüşümlü işlenir → tüm Türkiye
  zaman içinde kapsanır
- Shell botuna 1800 sn (diğerleri 300 sn) timeout ve hata toleransı tanınır
  (`scraper/run_all_bots.py`)

İstasyon envanteri (konum/isim/koordinat) ayrı botlarla gelir: Shell için
`find.shell.com/tr/fuel` (`scraper/shell_station_bot.py`), ayrıca TP ve Total envanter
botları.

### Zamanlama
`.github/workflows/otopilot.yml` (GitHub Actions cron):

- **Fiyatlar:** günde 4× — 06:20 / 12:20 / 18:20 / 00:20 (TR saati)
- **Haberler:** günde 2×
- **İstasyon envanteri:** haftada 1 (Pazar)
- Manuel tetikleme (`workflow_dispatch`) ve `dry_run` desteklenir

### Yazım mantığı ("değişmişse yaz")
Botlar veriyi körlemesine yazmaz; önce mevcut fiyatı çeker, **diff** yapar
(`scraper/database_writes.py`):

- Fiyat değişmişse → `price_status = 'fresh'` upsert
- Değişmemiş ama statü `fresh` değilse ya da 24 saatten eskiyse → tazelik güncellemesi
- Değişmemiş ve `fresh` ise → **atla** (gereksiz yazım yok)

Tablolar: `fiyatlar` (`on_conflict = istasyon_id,yakit_tipi`), `istasyonlar`,
`fiyat_gecmisi`. Yazma, `FULLET_DRY_RUN` / `FULLET_ALLOW_DB_WRITE` env kapılarıyla
korunur; workflow yalnızca canlı koşuda yazmaya izin verir.

### Otomatik "eskitme" (staleness)
Bot bir süre çalışmazsa kullanıcı eski fiyatı "güncel" sanmasın diye Postgres içinde
`pg_cron` job'ları çalışır (`database/auto_price_staleness.sql`):

- Her saat :05 — 12 saatten eski `fresh` → `stale`
- Her saat :10 — 48 saatten eski `stale` → `unknown`
- Her gün 03:00 — 7 gün güncellenmeyen istasyon → `visibility_status = low_priority`
- Her Pazar 04:00 — 90 günlük kullanılmayan push token'ları sil

**Kaynak dosyalar:** `scraper/{shell_bot,shell_station_bot,run_all_bots,database_writes,db_utils,config}.py`

---

## 4. Backend Stack — Supabase (ana) + Firebase (yardımcı)

> ⚠️ **Sık karışan nokta:** Fullet bir "Firebase uygulaması" değildir.
> **Firebase = kimlik + analitik + çökme raporu.**
> **Supabase = tüm veri ve backend.**

### Supabase (ana backend)
- **Postgres** — `istasyonlar`, `fiyatlar`, `fiyat_gecmisi`, `haberler`, `push_tokens`,
  `price_alerts`, admin gözlem tabloları (`app_heartbeats`, `bot_runs`, `system_alerts`)
- **PostGIS** — konum sorgusu. `get_nearby_stations` RPC'si `ST_DWithin` ile yarıçap
  filtreler, `konum <-> ST_MakePoint(...)` ile mesafeye göre sıralar, GIST index kullanır
- **RLS** — herkes okur, yazma yalnızca service-role botlarında
- **pg_cron** — zamanlı görevler (bkz. §3 eskitme)
- **Edge Functions (Deno)** — `fiyat-push` toplu bildirim gönderimi
- **RPC (SECURITY DEFINER)** — `record_app_heartbeat`, `is_fullet_admin` vb.

### Firebase (yalnızca üç iş)
`fullet_flutter/pubspec.yaml`: `firebase_core`, `firebase_auth`, `firebase_analytics`,
`firebase_crashlytics` (+ `google_sign_in`). Proje: `fullet-d59c7` (yalnızca Android).

- **Auth** — Google ile Giriş. Girişte `SupabaseService.upsertUserProfile` ile Supabase
  `fullet_users` tablosuna profil senkronlanır. Auth **opsiyoneldir**; uygulama giriş
  yapmadan tam çalışır, girişin tek işlevsel faydası favori senkronudur.
- **Analytics** — kullanım event'leri (`station_tapped`, `search_performed`, ...)
- **Crashlytics** — çökme raporları

> **FCM (Firebase Cloud Messaging) kullanılmıyor.** `firebase_messaging` paketi projede
> yoktur; push için Expo Push API kullanılır (bkz. §7).

---

## 5. Güvenlik Modeli (RLS)

Prensip (`database/rls_policies.sql`): *"Public read, writes behind service role."*

- **`istasyonlar`** — SELECT yalnızca `aktif IS TRUE AND visibility_status IN
  ('visible','low_priority')`. Ek bir `RESTRICTIVE` politika ile zorlanır → gizli
  istasyonlar hiçbir koşulda sızmaz.
- **`fiyatlar` / `fiyat_gecmisi` / `haberler`** — public okuma (`USING (true)`).
- **`push_tokens`** — yalnızca INSERT; `WITH CHECK` ile token uzunluğu 20–4096 ve
  `provider IN ('fcm','expo','apns')`.
- **Admin tabloları** — `is_fullet_admin()` (SECURITY DEFINER; `admin_emails`'e bakar).
  Anonim uygulama tabloya doğrudan yazamaz, yalnızca `record_app_heartbeat` RPC'siyle
  15 dakikada bir heartbeat gönderir.
- **CHECK constraint'ler** — fiyat 5–200 TL, koordinat Türkiye sınırı; PostGIS trigger'lar
  koordinattan `konum` üretir ve fiyat değişince `fiyat_gecmisi`'ne log yazar.

**Kaynak dosyalar:** `database/{rls_policies,production_hardening,admin_observability}.sql`

---

## 6. Mobil Uygulama Özellikleri

Uygulama **tek harita ekranı** mimarisindedir (`lib/screens/modern_map_screen.dart`);
diğer her şey bottom-sheet / overlay olarak açılır.

### Konum bazlı istasyon bulma
1. **GPS** — `geolocator` ile kademeli strateji (medium → low → last known → Türkiye
   merkezi fallback). Türkiye sınırı dışındaki konum reddedilir.
2. **PostGIS sorgusu** — `SupabaseService.fetchStations()` → `get_nearby_stations` RPC.
   Hata durumunda katmanlı fallback: legacy RPC → tüm istasyonları çekip Haversine ile
   yerel filtreleme (`lib/utils/distance_calculator.dart`), 5 dk cache.
3. **Google Maps** — açık/koyu harita stili, zoom bazlı declutter ve **kümeleme**
   (`google_maps_cluster_manager_2`).

### Öne çıkan işlevler
- **Yakıt tipi filtresi** — Benzin / Motorin / LPG / Elektrik
- **Marka filtresi** — Shell, Opet, PO, ...
- **Odak modu** — `smart` / `cheapest` / `nearest` (`lib/models/map_focus_mode.dart`)
- **Akıllı istasyon skoru** — sadece litre fiyatı değil; tank kapasitesi + araç tüketimi
  + istasyona gitme mesafe maliyetini toplayıp 0–100 puanla en mantıklı istasyonu bulur
  (`lib/services/smart_station_service.dart`). **Ana ayırt edici özellik.**
- **Garaj** — araç marka/model DB'si, tank ve tüketim bilgisi; akıllı skoru besler
  (`lib/widgets/garage_modal.dart`, `lib/utils/car_database.dart`)
- **Arama** — tüm istasyonlarda; son bakılanlar + favoriler
- **Favoriler** — yerel (SharedPreferences) + giriş yapılırsa Supabase senkron
- **Sürüş modu** — canlı GPS akışı, kamera takibi, yakındaki hedef banner + tek tuşla
  Google Maps yol tarifi
- **Fiyat trendi** — sparkline (`lib/widgets/price_trend_sparkline.dart`)
- **Haberler** — `haberler` tablosundan yan menüde
- **Fiyat güvenilirlik göstergesi** — `price_status` üzerinden `fresh` / `stale` /
  `unknown` ayrımı; hesaplamada yalnızca güvenilir fiyat kullanılır
  (`lib/models/station.dart`)

### İlk açılış akışı
3 sayfalık onboarding (`lib/screens/onboarding_screen.dart`) → "Aracımı ekle" ile garaj
modalı → harita ekranı. Sonraki açılışlar doğrudan haritaya gider; harita kaydırıldıkça
(`onCameraIdle`, 450 ms debounce) yeni bölge otomatik sorgulanır.

---

## 7. Bildirimler

| Tür | Durum | Nasıl |
|-----|-------|-------|
| Sunucu toplu push | ✅ Çalışıyor | Botlar fiyatı güncelleyince Edge Function `fiyat-push`'a POST → **Expo Push API** ile tüm token'lara zam/güncelleme bildirimi |
| Yerel hatırlatıcılar | ✅ Çalışıyor | `flutter_local_notifications` + `timezone` — 5 gün sonra "yakıt zamanı", garaj kurulmamışsa 24 saatlik hatırlatıcı |
| Kişisel fiyat alarmı | ⚠️ **Yarım / planlı** | `price_alerts` tablosu (`esik_fiyat`) hazır ama Flutter/Python/Edge Function'da okunmuyor — eşik karşılaştırma mantığı ve UI henüz yok |

**Kaynak:** `supabase/functions/fiyat-push/index.ts`, `scraper/{database_writes,summary_push}.py`,
`fullet_flutter/lib/services/notification_service.dart`, `database/sprint4_price_alerts.sql`

---

## 8. Admin Panel

Web tabanlı operasyon paneli (`admin_panel/`): **React 19 + Vite 7**, GitHub Pages'te
yayında. Yalnızca Supabase **anon key** kullanır (service-role içermez); erişim RLS +
`is_fullet_admin()` ile korunur.

- Giriş: Supabase magic-link (OTP); `admin_emails`'te olmayan e-posta panele giremez
- Gösterge: anlık / 24s / 7g / 30g aktif cihaz sayısı, marka bazlı veri sağlığı
  (bayat/temiz), açık sistem alarmları, son bot çalışmaları, haber akışı

---

## 9. Teknoloji Özet Tablosu

| Katman | Teknoloji |
|--------|-----------|
| Mobil uygulama | Flutter (Dart), Provider, google_maps_flutter, geolocator |
| Ana backend / DB | Supabase Postgres + PostGIS + RLS + pg_cron + Edge Functions (Deno) |
| Mobil Auth | Firebase Auth (Google Sign-In) → Supabase profiline senkron |
| Analytics / Crash | Firebase Analytics + Crashlytics |
| Push (sunucu) | Edge Function `fiyat-push` → Expo Push API (FCM kullanılmıyor) |
| Push (yerel) | flutter_local_notifications + timezone |
| Veri toplama | Python botlar (scraper/), GitHub Actions cron, service-role yazma |
| Admin panel | React 19 + Vite 7, Supabase anon key, GitHub Pages |

---

## 10. Kısa Cevaplar (SSS)

**Fiyat verisini nereden çekiyorsunuz, API mi?**
Kısmen. Opet ve Total resmi JSON API sunuyor; diğer markalar için web sitelerini
scraping yapan kendi Python botlarımız var. Shell'i headless Chromium (Playwright) ile
il/ilçe gezerek topluyoruz. Hepsi GitHub Actions'ta günde 4× otomatik çalışıyor.

**Firebase'in hangi servislerini kullandınız?**
Yalnızca Auth (Google Sign-In), Analytics ve Crashlytics. Veri/backend Firebase'de
değil, Supabase'de. FCM push da kullanmıyoruz (Expo ile gönderiyoruz).

**Konum bazlı istasyon bulma var mı?**
Evet, çekirdek özellik. GPS + PostGIS `get_nearby_stations` + Google Maps kümeleme +
canlı sürüş modu.

**Bildirim var mı?**
Sunucudan toplu zam/güncelleme push'u ve uygulama içi yerel hatırlatıcılar var. Kişisel
eşik-fiyat alarmı ise henüz aktif değil (tablo hazır, kod bağlantısı yok).
