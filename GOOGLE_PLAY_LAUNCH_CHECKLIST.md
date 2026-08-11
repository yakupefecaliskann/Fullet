# Fullet — Google Play Yayın Checklist'i

**Son güncelleme:** 11 Ağustos 2026
**Kapsam:** Bu dosya Play yayınıyla ilgili TEK doğruluk kaynağıdır. (Eski
`PLAY_STORE_READINESS.md` buraya birleştirildi; Data Safety tablosu aşağıdadır.)

---

## 0. Durum Panosu — 11 Ağustos 2026

**Uygulama Google Play'de CANLI.** İlk yayın süreci kapandı; aşağıdaki tablo artık
"yayına çıkış" değil, **açık kalan operasyonel işleri** takip ediyor.

### ✅ Kapananlar

| İş | Kanıt / tarih |
|---|---|
| Kod denetimi — tüm bulgular (B1, B2, H1–H4, M1–M5, L1–L6) | `dart analyze` → *No issues found!* · `flutter test` → 45/45 · `docs/KOD_DENETIM_ARSIVI.md` §A |
| Build zinciri: `targetSdk 36`, `minSdk 24`, AGP 8.11.1 / Gradle 8.14 / Kotlin 2.3.10 / NDK 27 | commit `ccd3bc7` |
| Upload key reset | Google onayladı; AAB kabul edildi (§2.1) |
| İlk yayın | Uygulama Play'de yayınlandı |
| **1.0.4+7 (garaj düzeltmesi)** | 11 Ağu 2026 — **onaylandı, Üretim'de Etkin** |
| Data Safety formu | §3'teki tabloya göre dolduruldu |
| W2 / ASO: başlık, kısa + uzun açıklama, 6 yeni vitrin görseli | 11 Ağu 2026 — tek seferde incelemeye gönderildi (§2.4) |

### ⏳ Açık kalanlar

| # | İş | Kim | Not |
|---|---|---|---|
| 1 | **App signing SHA-1 Maps anahtarında mı?** | 👤 | 🔴 Eksikse Play'den kuran herkeste harita boş açılır. Uygulama canlı ve şikâyet yok — büyük olasılıkla eklendi, ama Cloud Console'dan **gözle doğrulanmalı**. §2.2 |
| 2 | API restrictions → yalnızca **Maps SDK for Android** | 👤 | §2.2 |
| 3 | Kota + bütçe uyarısı kur | 👤 | "Sıfır maliyet" hedefi için sürpriz fatura riski. §2.2 |
| 4 | W2 ASO incelemesinin sonucu | Google | Gönderildi, sonuç bekleniyor. **Yeni bir değişiklik göndermek bekleyen incelemeyi sıfırlar** — önce sonucu gör |
| 5 | Android 15/16 cihazda edge-to-edge doğrulaması | 👤 | Test cihazı API 33; API 36 davranışı orada tetiklenmiyor |
| 6 | `build/symbols/1.0.4+7` arşivle | 👤 | Yoksa bu sürümün Crashlytics stack trace'leri okunamaz. §6 |

---

## 1. Mevcut Teknik Durum

| Alan | Değer |
|---|---|
| Paket adı | `com.fullet.app` |
| Sürüm | `1.0.4+7` (versionName 1.0.4, versionCode 7) — 11 Ağustos 2026'da **onaylandı, Üretim'de Etkin**. AAB `android-arm,android-arm64` hedefleriyle üretildi (android-x64 bu makinedeki Uygulama Denetimi ilkesi tarafından engellendiği için dışlandı — bkz. `RELEASE_NOTES.md`). |
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
`viewPadding.bottom` kadar yukarı itiliyor. Android 13 cihazda doğrulandı;
**API 35+ bir cihazda tekrar bakılmalı** (bkz. `RELEASE_QA_CHECKLIST.md`).

**Kod sağlığı:** `dart analyze` → *No issues found!* · `flutter test` → 45/45 ·
R8 küçültme + `--obfuscate` açık. Denetim raporu kapatıldı
(`docs/KOD_DENETIM_ARSIVI.md` §A).

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

**Durum:** ✅ **KAPANDI.** Talep 4 Ağustos 2026'da gönderildi (Play Console →
*Release* → *Setup* → *App integrity* → *App signing* → *Request upload key reset*,
`upload_certificate.pem` yüklendi), Google onayladı ve sonraki AAB'ler kabul edildi.

Aşağıdaki keystore bilgileri **hâlâ geçerli referanstır** — her yayında bu
anahtarla imzalanır.

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

**Durum — 4 Ağustos 2026:** ✅ Anahtar *Android apps* olarak kısıtlandı;
paket adı `com.fullet.app` + **yeni upload sertifikası SHA-1**
(`49:7B:9C:C2:DF:7F:94:93:65:F6:B8:0A:35:CB:7F:94:44:CD:67:E2`) eklendi.
Eski `40:9B:C1:...` değeri geçersizdir, kaldırılabilir.

> 🔴 **HENÜZ BİTMEDİ — App signing SHA-1 eksik.**
> Play App Signing devrede olduğunda kullanıcıların telefonuna giden APK,
> senin upload anahtarınla **değil**, Google'ın kendi *app signing* anahtarıyla
> yeniden imzalanır. Maps anahtarında yalnızca upload SHA-1'i varsa,
> **Play'den kuran her kullanıcıda harita boş/gri açılır** — senin cihazında
> (yandan yükleme) sorunsuz göründüğü için bu hata kolayca gözden kaçar.
>
> **İlk başarılı AAB yüklemesinden sonra:** Play Console → *App integrity* →
> *App signing key certificate* → SHA-1'i kopyala → Cloud Console'da Maps
> anahtarına **ikinci bir Android kısıtlaması** olarak ekle. İki SHA-1 de listede
> kalmalı (upload = yerel testler, app signing = Play'den kuran kullanıcılar).

Kalan alt maddeler:

- [ ] **App signing SHA-1** eklendi (yukarıdaki uyarı — ilk yüklemeden sonra)
- [ ] API restrictions → yalnızca **Maps SDK for Android**
- [ ] Kota + bütçe uyarısı ("sıfır maliyet" hedefi için sürpriz fatura riski)

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

> **11 Ağustos 2026:** Başlık zaten `FULLET_GROWTH_STRATEGY.md` §5.2 önerisiyle
> uyumluydu (`Fullet: Akaryakıt Fiyatları`). Kısa açıklama (§5.3) ve uzun
> açıklama (Ek A) Play Console → Varsayılan mağaza girişi'nde güncellenip
> **taslak olarak kaydedildi**, **incelemeye gönderilmedi** — 1.0.4+7'nin
> devam eden Play incelemesini iptal edip yeniden başlatmamak için 1.0.4+7
> onaylanana kadar bekletiliyor. Ekran görüntüsü caption'ları (§5.5) henüz
> yapılmadı: yeni görsel üretimi gerekiyor.
> **11 Ağustos 2026 (kapanış):** 1.0.4+7 onaylandı, Üretim'de Etkin. Cihazdan
> alınan 6 taze ekran görüntüsü Canva'da §5.5 caption'larıyla 1080×1920
> vitrin görseline dönüştürüldü, eski 6 görsel silindi, doğru sırayla
> yüklendi. Kısa/uzun açıklama + 6 ekran görüntüsü tek seferde Google
> incelemesine gönderildi (1.0.4+7 zaten onaylı olduğu için risksiz).

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
