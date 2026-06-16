# Fullet Google Play Hazırlık Notları

Son kontrol tarihi: 2026-05-09

## Teknik Durum

- Paket adı: `com.fullet.app`
- Minimum SDK: `21`
- Target SDK: `35`
- Uygulama sürümü: `1.0.2+3`
- Release APK komutu: `flutter build apk --release --build-name 1.0.2 --build-number 3`
- Play için tercih edilen paket: `flutter build appbundle --release --build-name 1.0.2 --build-number 3`
- Yayın öncesi tam kontrol: `powershell -ExecutionPolicy Bypass -File .\scripts\release_check.ps1 -BuildAab`

## Yayın Öncesi Kırmızı Çizgiler

- `python scraper\backend_health_check.py` temiz bitmeden yayın yok.
- Canli DB'de `database/production_hardening.sql`, `database/add_status_columns.sql`, `database/create_postgis_rpc.sql` ve `database/rls_policies.sql` bu sirayla calismis olmali.
- `database/live_public_schema_fix.sql` legacy onarim betigidir; normal yayin hazirliginda calistirilmaz.
- `verify_live_schema.sql` çıktısında `fiyatlar_veri_kaynagi_exists`, `push_tokens_provider_exists`, `istasyonlar_rls_enabled` ve `istasyonlar_anon_policy_filters_active` true dönmeli.
- Anon kullanıcı pasif istasyonları okuyamamalı. Health check bunu artık direkt fail eder.
- Fiyat ve istasyon verisi sadece resmi kaynaklardan gelmeli; sahte/tahmini fiyat canlıya yazılmayacak.

## Google Play Kontrolleri

- Google Play'in resmi hedef API dokümanı, 31 Ağustos 2025 itibarıyla yeni uygulama ve güncellemeler için Android 15/API 35 veya üstünü istiyor. Fullet şu an `targetSdkVersion 35` ile bu eşiği karşılıyor.
- Play App Signing kullanılmalı. Play Console'da App signing kurulumu tamamlanmadan AAB yükleme süreci bitmiş sayılmaz.
- Google Maps API key mutlaka Android paket adı `com.fullet.app` ve Play/App upload certificate SHA-1 değerleriyle kısıtlanmalı.
- Google Maps için kota ve bütçe uyarısı açılmalı. "0 maliyet" hedefi için fatura sürprizi bırakılmayacak.
- Data safety formu, uygulamanın gerçek veri kullanımına göre doldurulmalı.
- Privacy policy public, aktif, PDF olmayan, düzenlenemez bir URL'de yayınlanmalı ve uygulama içinden erişilebilir olmalı: `https://yakupefecaliskann.github.io/Fullet/privacy.html`
- Store görselleri gerçek cihaz ekran görüntülerinden seçilmeli.
- Launcher icon Fullet markalı ikonla değiştirildi. Play Store 512x512 ikon kaynağı: `fullet_flutter\assets\brand\fullet_play_icon_512.png`

## Data Safety Taslağı (kodla doğrulanmış — 16 Haziran 2026)

> **ÖNEMLİ DÜZELTME:** Önceki taslak "hesap açtırmaz, analytics SDK kullanmaz" diyordu; bu YANLIŞTI. `pubspec.yaml` `firebase_analytics` + `firebase_crashlytics` içeriyor ve `auth_service.dart` Google Sign-In ile ad/e-posta topluyor. Aşağıdaki tablo gerçek davranışa göre düzeltilmiştir. Play Console Data Safety formu bununla doldurulmalı.

**Genel:** Data shared with third parties = **No** (Firebase, hizmet sağlayıcı sıfatıyla işler). Data encrypted in transit = **Yes** (HTTPS). Users can request data deletion = **Yes** → `https://yakupefecaliskann.github.io/Fullet/data-deletion.html`. Reklam SDK'sı / reklam kimliği = **Yok**.

| Data Safety kategorisi | Tür | Toplanıyor mu | Amaç | Zorunlu/İsteğe bağlı | Kaynak |
|---|---|---|---|---|---|
| **Location** | Approximate + Precise location | Evet | App functionality | İsteğe bağlı (konum izni reddedilebilir) | `geolocator` + `get_nearby_stations` RPC. Geçmiş tutulmaz. |
| **Personal info** | Name, Email address | Evet | App functionality, Account management | **İsteğe bağlı** (yalnızca Google ile giriş yapılırsa) | `auth_service.dart` → `fullet_users` |
| **App activity** | App interactions, Search history, Other user-generated content | Evet | Analytics | Zorunlu (otomatik) | `analytics_service.dart` (Firebase Analytics) — arama sorgusu dahil |
| **App info & performance** | Crash logs, Diagnostics | Evet | Analytics, App functionality | Zorunlu (otomatik) | `firebase_crashlytics` (main.dart) |
| **Device or other IDs** | Device or other IDs | Evet | Analytics | Zorunlu (otomatik) | Firebase Analytics instance ID + anonim heartbeat (`app_heartbeat_service.dart`) |

- **Yerel (toplanmayan, cihazda kalan):** Seçili yakıt, garaj bilgisi, favoriler, son bakılan istasyonlar `shared_preferences` ile cihazda saklanır — Data Safety'de "toplanan" sayılmaz.
- **İçerik:** Resmi kaynaklardan toplanmış istasyon/fiyat/haber verileri Supabase üzerinden okunur (kullanıcıdan veri değil).
- **Harici açılışlar:** Yol tarifi için Google Maps, haberler için dış tarayıcı/uygulama açılabilir.
- **Hesap silme:** Google ile giriş bir "account" oluşturduğu için Play, hesap+veri silme yolu ister → `data-deletion.html` bu yolu sağlıyor (e-posta talebi, 30 gün içinde silme).

## Resmi Referanslar

- Target API: https://support.google.com/googleplay/android-developer/answer/11926878
- Play App Signing: https://support.google.com/googleplay/android-developer/answer/9842756
- User Data / Privacy Policy: https://support.google.com/googleplay/android-developer/answer/9888076
- Data safety: https://support.google.com/googleplay/android-developer/answer/10787469
