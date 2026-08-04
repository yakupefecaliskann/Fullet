# Fullet — Google Play Yayın Checklist'i

**Son güncelleme:** 4 Ağustos 2026
**Kapsam:** Bu dosya Play yayınıyla ilgili TEK doğruluk kaynağıdır. (Eski
`PLAY_STORE_READINESS.md` buraya birleştirildi; Data Safety tablosu aşağıdadır.)

---

## 1. Mevcut Teknik Durum

| Alan | Değer |
|---|---|
| Paket adı | `com.fullet.app` |
| Sürüm | `1.0.3+6` (versionName 1.0.3, versionCode 6) |
| minSdkVersion | **24** (Android 7.0) — 4 Ağu 2026'da 21'den yükseltildi, Android 5.x desteği bilinçli olarak bırakıldı |
| targetSdkVersion | **36** (Android 16) — Play'in 31 Ağustos 2026 eşiğini karşılar |
| compileSdkVersion | 36 |
| Android Gradle Plugin | 8.11.1 |
| Gradle | 8.14 |
| NDK | 27.0.12077973 |
| Kotlin | 2.3.10 |
| Play'e yüklenecek dosya | `fullet_flutter/build/app/outputs/bundle/release/app-release.aab` |

**Edge-to-edge:** Android 16'da opt-out kaldırıldı. Uygulama `SystemUiMode.edgeToEdge`
ile açıkça edge-to-edge çalışıyor; alt panel, yan menü ve harita FAB'ları
`viewPadding.bottom` kadar yukarı itiliyor. **Gerçek cihazda görsel doğrulama şart**
(bkz. `RELEASE_QA_CHECKLIST.md`).

---

## 2. Yayından Önce Bloklayan İşler

### 2.1 Upload key reset (🔴 KRİTİK — Play Console'da yapılacak)

**Eski upload keystore kalıcı olarak kaybedildi.** (Depoda 31 Temmuz 2026 tarihli bir
AAB duruyordu ama o paket upload anahtarıyla değil, bir *Smoke Test* sertifikasıyla
imzalanmıştı — yani zaten yüklenebilir değildi.) 4 Ağustos 2026'da **yeni bir upload
keystore üretildi.**

| | Değer |
|---|---|
| Keystore | `fullet_flutter/android/upload-keystore.jks` (PKCS12, RSA 4096) |
| Alias | `fullet-upload` |
| Geçerlilik | 4 Ağu 2026 → **20 Ara 2053** |
| **SHA-1** | `49:7B:9C:C2:DF:7F:94:93:65:F6:B8:0A:35:CB:7F:94:44:CD:67:E2` |
| **SHA-256** | `60:EF:89:72:9C:88:DF:B9:2C:7C:65:2B:DE:F3:FE:AD:DB:37:CA:3C:C3:86:B3:DD:57:8C:4A:C2:75:96:B2:B7` |
| Play'e verilecek sertifika | `fullet_flutter/android/upload_certificate.pem` |

**Yapılacak:** Play Console → *Release* → *Setup* → *App integrity* → *App signing* →
**Request upload key reset** → yukarıdaki `upload_certificate.pem` dosyası yüklenir.
Google onaylayana kadar (genelde 1–2 iş günü) yeni anahtarla imzalanmış AAB **reddedilir**.

> ⚠️ Bu bir kerelik bir işlem değil, **geri alınamaz bir kayıp deneyimi.** Yeni keystore
> ve parolası kaybolursa aynı süreç baştan gerekir. `key.properties` ve `.jks` git'e
> girmez (`.gitignore`'da) — bu doğru davranıştır, ama depo kopyalanınca/taşınınca da
> gelmez. **Her ikisinin de depo dışında, yedekli bir kopyası tutulmalıdır**
> (parola yöneticisi + ikinci fiziksel kopya).

- Kurulum şablonu: `fullet_flutter/android/key.properties.example`
- `key.properties` yoksa `flutter build appbundle --release` **imzasız** paket üretir
  (build.gradle bunu artık açık bir uyarıyla söylüyor) ve Play yüklemeyi reddeder.
- Üretilen paketi her zaman doğrula:
  `powershell -ExecutionPolicy Bypass -File .\scripts\verify_aab_signature.ps1`

### 2.2 Google Maps API key kısıtlaması

- Android package: `com.fullet.app`
- **Yeni** upload sertifikası SHA-1 (`49:7B:9C:...:67:E2`) eklenmeli.
  Eski `40:9B:C1:...` değeri artık geçersizdir, kaldırılabilir.
- Play App Signing açıldıktan sonra Google'ın verdiği **App signing SHA-1** de eklenmeli.
- API restrictions → yalnızca **Maps SDK for Android**.
- Kota + bütçe uyarısı açılmalı ("sıfır maliyet" hedefi için sürpriz fatura riski).

### 2.3 Gizlilik politikası

- Canlı URL: `https://yakupefecaliskann.github.io/Fullet/privacy.html`
- Kaynak dosya: `admin_panel/public/privacy.html` (tek doğruluk kaynağı).
- Play; herkese açık, aktif, PDF olmayan ve düzenlenemez bir URL istiyor.
- Hesap + veri silme: `https://yakupefecaliskann.github.io/Fullet/data-deletion.html`

### 2.4 Store listing

- Kısa açıklama, uzun açıklama, kategori, iletişim e-postası.
- Görseller hazır: `play_store_assets/upload/` (telefon 6 + 7"/10" tablet),
  feature graphic 1024×500, 512×512 ikon
  (`fullet_flutter/assets/brand/fullet_play_icon_512.png`).
- Açıklamada **"fiyatlar resmi/marka kaynaklarından; tahmini fiyat gösterilmez"**
  vurgusu bulunmalı.
- Sürüm notu metni: `RELEASE_NOTES.md`

### 2.5 Test süreci

- İlk adım **Internal testing**, sonra **Closed testing**.
- Hesap 13 Kasım 2023'ten sonra açıldıysa production için **12 tester × 14 gün
  kesintisiz opt-in** zorunlu.
- Production'a kademeli rollout (%20 → %50 → %100); ilk crash dalgası Crashlytics'te izlenir.

---

## 3. Data Safety Formu (kodla doğrulanmış)

**Genel:** Data shared with third parties = **No** (Firebase, hizmet sağlayıcı sıfatıyla
işler) · Data encrypted in transit = **Yes** (HTTPS) · Users can request data deletion =
**Yes** → `data-deletion.html` · Reklam SDK'sı / reklam kimliği = **Yok**.

| Data Safety kategorisi | Tür | Amaç | Zorunlu/İsteğe bağlı | Kaynak |
|---|---|---|---|---|
| **Location** | Approximate + Precise | App functionality | İsteğe bağlı (izin reddedilebilir) | `geolocator` + `get_nearby_stations` RPC. Konum geçmişi tutulmaz. |
| **Personal info** | Name, Email | App functionality, Account management | İsteğe bağlı (yalnızca Google ile giriş) | `auth_service.dart` → `fullet_users` |
| **App activity** | App interactions, Search history, Other UGC | Analytics | Zorunlu (otomatik) | `analytics_service.dart` (Firebase Analytics) |
| **App info & performance** | Crash logs, Diagnostics | Analytics, App functionality | Zorunlu (otomatik) | `firebase_crashlytics` (`main.dart`) |
| **Device or other IDs** | Device or other IDs | Analytics | Zorunlu (otomatik) | Firebase Analytics instance ID + `app_heartbeat_service.dart` |

- **Cihazda kalan (toplanmayan):** seçili yakıt, garaj bilgisi, favoriler, son bakılan
  istasyonlar → `shared_preferences`. Data Safety'de "toplanan" sayılmaz.
- **İçerik:** istasyon/fiyat/haber verisi resmi kaynaklardan toplanır, kullanıcıdan veri değildir.
- **Harici açılışlar:** yol tarifi için Google Maps, haberler için dış tarayıcı.

---

## 4. Backend Kırmızı Çizgileri (yayın öncesi)

- `python scraper\backend_health_check.py` temiz bitmeden yayın yok.
- Canlı DB'de şu betikler bu sırayla çalışmış olmalı:
  `database/production_hardening.sql` → `database/add_status_columns.sql` →
  `database/create_postgis_rpc.sql` → `database/rls_policies.sql`
- `database/live_public_schema_fix.sql` legacy onarım betiğidir; normal yayın
  hazırlığında çalıştırılmaz.
- `verify_live_schema.sql` çıktısında `fiyatlar_veri_kaynagi_exists`,
  `istasyonlar_rls_enabled` ve `istasyonlar_anon_policy_filters_active` **true** dönmeli.
- Anon kullanıcı pasif istasyonları okuyamamalı (health check bunu fail eder).
- Fiyat ve istasyon verisi **sadece resmi kaynaklardan** gelmeli; tahmini fiyat
  canlıya yazılmaz.

---

## 5. Bot Otomasyonu

- Workflow: `.github/workflows/otopilot.yml`
- Fiyat botları: her gün ~06:20, 12:20, 18:20, 00:20 (TR saati)
- Haber botu: her gün ~08:50 ve 20:50 · İstasyon envanteri: pazar ~04:40
- Gerekli GitHub secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
  (veya service-role taşıyan `SUPABASE_KEY`), `SUPABASE_ANON_KEY`
- `SUPABASE_ANON_KEY` yoksa botlar yazabilir ama RLS/public okuma health check'i kırmızıya düşer.
- **Bakım sınırı:** GitHub Actions zamanlanmış workflow'lar 60 gün repo aktivitesi
  olmazsa devre dışı kalır. Her ~8 haftada bir commit (veya manuel "Enable") gerekir.

---

## 6. Yayın Öncesi Komut

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release_check.ps1 -BuildAab
```

Bu komut sırasıyla: backend health check → ops report → backend unit testleri →
`flutter analyze --no-fatal-infos` → `flutter test` → obfuscated release AAB →
**imza doğrulaması** çalıştırır. Herhangi bir adım kırmızıysa paket yüklenmez.

> **Sembol arşivi (zorunlu):** Release derlemesi `--obfuscate` kullanıyor.
> Sembol dosyaları `fullet_flutter/build/symbols/<sürüm>` altına yazılır ve
> **her yayınla birlikte arşivlenmelidir**. O klasör olmadan ilgili sürümün
> Crashlytics'teki Dart stack trace'leri kalıcı olarak okunamaz.

---

## 7. Resmi Referanslar

- Target API: https://support.google.com/googleplay/android-developer/answer/11926878
- Play App Signing: https://support.google.com/googleplay/android-developer/answer/9842756
- Data Safety: https://support.google.com/googleplay/android-developer/answer/10787469
- User Data / Privacy Policy: https://support.google.com/googleplay/android-developer/answer/9888076
- Yeni kişisel hesap test şartları: https://support.google.com/googleplay/android-developer/answer/14151465
