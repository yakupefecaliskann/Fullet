# Fullet — Kod Denetimi Arşivi (KAPALI)

Bu dosya iki **kapatılmış** denetim raporunun birleşimidir. İkisi de tarihsel
kayıttır: içlerindeki bulguların tamamı düzeltilmiş ve doğrulanmıştır. Aktif bir
iş listesi değildir — güncel yayın durumu için `GOOGLE_PLAY_LAUNCH_CHECKLIST.md`,
her sürümde tekrarlanan kontroller için `RELEASE_QA_CHECKLIST.md`.

**Neden siliniyor değil de saklanıyor:** kararların *gerekçesi* burada. Örneğin
`win32` bağımlılığının neden ölü olmadığı, `_fetchStationsLegacy` /
`_fetchStationsByBrandsWholeCountry` zincirinin neden silinmemesi gerektiği ve
minSdk 24'e çıkma kararının bilinçli olduğu yalnızca bu raporlarda yazılı. Bu
bilgi olmadan bir sonraki temizlik turu çalışan kodu siler.

| Bölüm | Kaynak dosya (birleştirildi) | Kapsam | Kapanış |
|---|---|---|---|
| **A** | `FULLET_PRE_RELEASE_DENETIMI.md` | Yayın öncesi kod denetimi — 22 bulgu (B1, B2, H1–H4, M1–M5, L1–L6) | 4 Ağustos 2026 |
| **B** | `FULLET_KOD_SAGLIGI_YOL_HARITASI.md` | Tam kod sağlığı yol haritası — Faz 0–3 | 3 Ağustos 2026 |

> Her iki bölümün metni kaynak dosyalardan **birebir** taşınmıştır; özetlenmemiş
> veya kısaltılmamıştır. Başlık seviyeleri de olduğu gibi bırakılmıştır.

---
---

# ═══ BÖLÜM A ═══ Yayın Öncesi Kod Denetimi

*(kaynak: `FULLET_PRE_RELEASE_DENETIMI.md` — 4 Ağustos 2026'da kapatıldı)*

---

# Fullet — Yayın Öncesi (Pre-Release) Kod Denetimi

**Tarih:** 4 Ağustos 2026
**Kapsam:** `fullet_flutter/` (11.179 satır Dart, 35 dosya) + `scraper/` (9.778 satır Python) + Android release konfigürasyonu
**Denetim anındaki sürüm:** 1.0.2+5 (versionName 1.0.2, versionCode 5)

---

## ⚠️ GÜNCELLEME — 4 Ağustos 2026 (denetimden sonra yapılan işler)

Bu rapor artık salt bir denetim değil, **açık teknik borcun kaydıdır.** Aşağıdaki
bulgular kapatıldı; geri kalanlar hâlâ açıktır.

### ✅ Kapatıldı

| Bulgu | Ne yapıldı |
|---|---|
| **B1** — ASCII olmayan proje yolu | Proje `C:\Fullet`'e taşındı. `flutter analyze` artık çalışıyor (çıkış 255 → normal), `flutter build` AGP tarafından reddedilmiyor. |
| **B2** — targetSdkVersion 35 → 36 | `targetSdkVersion 36`. Araç zinciri yükseltildi: AGP 8.2.1 → **8.11.1**, Gradle 8.7 → **8.13**, Kotlin 1.9.22 → **2.3.10**, google-services 4.3.15 → 4.4.2, crashlytics 2.8.1 → 3.0.2. |
| **B2(b)** — minSdkVersion 21 → 24 | Kullanıcı onayıyla yapıldı. Android 5.0/5.1 desteği bilinçli olarak bırakıldı. |
| **B2(c)** — Android 16 edge-to-edge | `SystemUiMode.edgeToEdge` açıkça talep ediliyor; `systemNavigationBarColor` (API 35+'te no-op) şeffafa çekilip `systemNavigationBarContrastEnforced: false` eklendi. `StationBottomSheet`, yan menü listesi ve harita FAB/lejant offset'leri `viewPadding.bottom` kadar yukarı itildi. **Cihazda görsel doğrulama hâlâ gerekli.** |
| **M5** — `debugPrint` release'de log yazıyor | 20 çağrı tek bir `lib/utils/app_log.dart` → `appLog()` yardımcısına toplandı; gövde `kDebugMode` ile korunuyor, release AOT'de eleniyor. |
| **L3** — `android.enableJetifier` | Kaldırıldı. |
| Sürüm kodu | 1.0.2+5 → **1.0.3+6**. |
| **H1** — Sınırsız marker ikon önbelleği | `LinkedHashMap` tabanlı LRU'ya çevrildi, tavan **300 giriş** (`_DeclutterConfig` en fazla 110 marker çizdiği için ~3 ekran dolusu ikon sıcak kalır). Erişimde giriş "en yeni" konuma taşınır; tavan aşılınca `keys.first` (en uzun süredir kullanılmayan) düşer. 4 test: `test/marker_icon_cache_test.dart`. |
| **M1** — Arama sıralamadan ÖNCE kırpılıyor | Kırpma sıralamadan **sonraya** alındı. Sıralama/kırpma mantığı test edilebilir olsun diye `lib/utils/station_search.dart` içinde saf fonksiyonlara çıkarıldı (`rankStationSearchResults`, `rankStationsByPrice`); `_SearchResult` → public `StationSearchResult`. 7 test: `test/station_search_test.dart`. |

### 🔴 Denetimde görülmeyen, derleme sırasında çıkan bulgu

**Eklenti seti kurulu Flutter sürümüyle uyumsuzdu.** `flutter_plugin_android_lifecycle
2.0.19` ve `google_maps_flutter_android 2.8.0`, Flutter 3.44'te **kaldırılmış v1
embedding** sınıflarını kullanıyordu (`PluginRegistry.Registrar`,
`io.flutter.view.FlutterMain`) ve derleme kırılıyordu. Bu, B1 nedeniyle denetim
sırasında görünememişti — AGP yol kontrolü derlemeyi daha erken durduruyordu.

`flutter pub upgrade` ile kısıtlar içinde çözüldü (google_maps_flutter 2.5.3 → 2.14.2,
google_maps_flutter_android 2.8.0 → 2.19.12). Yeni Maps eklentisi kotlin-stdlib 2.3.10
getirdiği için Kotlin derleyicisi de 2.3.10'a çekilmek zorunda kaldı ve KGP sürümü
`settings.gradle` plugins bloğuna taşındı (kök `buildscript` classpath'i eklenti
alt-projelerine ulaşmıyor).

### ✅ Faz B / C / D — tamamı kapatıldı (4 Ağustos 2026)

| Bulgu | Ne yapıldı |
|---|---|
| **H4** — async hatalar Crashlytics'e ulaşmıyor | `PlatformDispatcher.instance.onError` kuruldu; Future zincirlerinde ve platform kanallarında oluşan yakalanmamış hatalar artık fatal olarak raporlanıyor. |
| **H2** — `_markersNotifier` dispose edilmiyor | `dispose()`'a eklendi. |
| **H3** — Her tercih değişiminde tam yeniden inşa | `didChangeDependencies` iki imzayla korumaya alındı: `_calcSignature` (yakıt/depo/tüketim) ve `_markerSignature` (+ favoriler). Favori eklemek artık akıllı hesabı yeniden koşmuyor, yalnızca marker seçimini tazeliyor; `rememberStation` hiçbir şey tetiklemiyor. İmzalar `_updateCalculationsAndMarkers` içinde de tazelendiği için açık çağrılarla oluşan **çift iş** de bitti. |
| **M3** — Bayat hata banner'ı | `_fetchStationsFromTableFallback` başarı yolunda `lastStationFetchError = null`. Tüm başarı yolları tarandı, hepsi temizliyor. |
| **M4** — Tema değişimi + override | `WidgetsBindingObserver` + `didChangePlatformBrightness` eklendi. Override artık `SharedPreferences`'a yazılıyor (kalıcı) ve tema düğmesine **uzun basınca** `null`'a dönüyor (sisteme geri dönüş yolu vardı yoktu). Harita stili `GoogleMap.style` parametresine bağlandı, `setState` ile kendiliğinden güncelleniyor. |
| **M2** — Arama normalizasyonu | `Station` üzerinde `searchHaystack`, `normalizedDisplayName`, `normalizedBrand` tembel önbellekli getter'lar. İstasyon başına bir kez hesaplanıyor; sıralama karşılaştırıcısı da bunları kullanıyor. |
| **L1** — Ölü bağımlılık | `google_maps_cluster_manager_2` pubspec'ten kaldırıldı; `Station with ClusterItem` mixin'i çıkarıldı (`location` getter'ı zaten sınıfın kendisindeydi). |
| **L2** — 77 deprecation | 73 × `withOpacity` → `withValues(alpha:)`, `Switch.activeColor` → `activeThumbColor`, `setMapStyle` → `GoogleMap.style`, `Supabase.anonKey` → `publishableKey`. `flutter_lints` ^2.0.0 → **^6.0.0**. **`dart analyze` artık "No issues found!"** |
| **L4/L5** — Küçültme ve sembol gizleme | `minifyEnabled` + `shrinkResources` açıldı, `android/app/proguard-rules.pro` eklendi. Release derlemesi `--obfuscate --split-debug-info` ile yapılıyor. |
| **L6** — `build()` içinde Future | `FulletApp` `StatefulWidget`'a çevrildi; başlangıç Future'ı State'te bir kez üretiliyor. |

> ⚠️ **Obfuscation'ın operasyonel bedeli:** Dart sembolleri gizlendiği için
> Crashlytics'teki Dart stack trace'leri, o sürümün
> `build/symbols/<sürüm>` klasörü olmadan **okunamaz**. `release_check.ps1`
> sembolleri sürüme göre ayrı klasöre yazıyor; bu klasör her yayınla birlikte
> arşivlenmelidir. Crash okunabilirliği sembol gizlemeden daha kıymetliyse
> `--obfuscate` bayrağı kaldırılabilir — AOT derlenmiş Dart kodu zaten
> kaynak biçiminde paketlenmiyor.

**Bu raporda açık bulgu kalmadı.**

---

## 🏁 Kapanış — 4 Ağustos 2026

Bu denetim **kapatılmıştır**. Rapordaki 22 bulgunun tamamı (B1, B2, H1–H4,
M1–M5, L1–L6) düzeltildi ve doğrulandı.

### Doğrulama kanıtı

| Kontrol | Denetim anı | Kapanışta |
|---|---|---|
| `dart analyze` | 74 info | **No issues found!** (`flutter_lints` ^6.0.0 altında) |
| `flutter analyze` | çıkış 255 (çöküyordu) | çalışıyor, temiz |
| `flutter test` | 33/33 | **45/45** (12 yeni regresyon testi) |
| `flutter build appbundle` | AGP reddediyordu | ✅ 52,8 MB, imzalı + obfuscated |
| Gerçek cihazda çalışma | **yapılamadı** (build üretilemiyordu) | ✅ Infinix X6528B / Android 13 |

### Cihaz testi (release derlemesi, Infinix X6528B, Android 13 / API 33)

Kurulan sürüm `1.0.3+6` · minSdk 24 · targetSdk 36. Süreç boyunca **crash
buffer tamamen boş**. R8 + obfuscation'ın hiçbir şeyi bozmadığı doğrulandı:

- Google Maps karoları, konum, Supabase istasyon/fiyat verisi
- Runtime marker PNG üretimi (taç renkleri dahil) — `MarkerIconFactory` çalışıyor
- Marka logosu asset'leri render oluyor → `shrinkResources` asset silmemiş
- Yakıt geçişi: 67.17 (Benzin) → 80.97 (Motorin), marker'lar doğru yeniden inşa edildi
- **M1 sahada doğrulandı:** "shell" araması 1.0 km → 3.0 km → 3.1 km sıralı
- Edge-to-edge: üst çubuk, alt panel, FAB yığını ve lejant kesilmiyor
- **M5 doğrulandı:** release logcat'te tek bir teşhis logu sızmıyor

### Kapsam dışı kalan (dürüst not)

- **Android 15/16 cihazda edge-to-edge doğrulaması yapılamadı.** Test cihazı
  API 33; API 36'nın *zorunlu* edge-to-edge davranışı orada tetiklenmiyor.
  Layout doğrulaması geçerlidir çünkü `SystemUiMode.edgeToEdge` açıkça talep
  ediliyor, ama API 36'ya özgü bir sürpriz ancak o cihazda görülebilir.
- **H1/H3'ün bellek ve FPS etkisi ölçülmedi.** Düzeltmeler kod okumasıyla
  doğru; büyüklüğü DevTools profillemesi gerektirir.
- **Tema uzun-basma (M4) görsel olarak teyit edilmedi** — SnackBar 2 sn sürüyor,
  ekran görüntüsü 3. sn'de alındı. Harita sistem temasıyla uyumlu döndü.

**Sonraki adımlar kodda değil, Play Console/Cloud Console tarafındadır:**
`GOOGLE_PLAY_LAUNCH_CHECKLIST.md` §0 durum panosuna bakınız.

---

## 0. Yönetici Özeti

Kod kalitesi beklenenden **iyi**: 33/33 test geçiyor, statik analizde tek bir warning/error yok
(74 bulgunun hepsi `info` seviyesinde deprecation), sıfır TODO/FIXME, sıfır yoruma alınmış kod
bloğu, sıfır çıplak `print()`, sıfır kullanılmayan private üye, sıfır hardcoded secret.
"Ölü ve kirli kod" başlığı büyük ölçüde **temiz çıktı** — bu, uydurulmuş bir bulgu listesi
yerine ölçümün sonucudur.

Buna karşılık **yayın yolu iki noktada fiilen kapalı**:

1. **Proje bu dizinden derlenemiyor.** `flutter build appbundle --release` Android Gradle
   Plugin tarafından reddediliyor çünkü proje yolu (`Masaüstü`) ASCII olmayan karakter içeriyor.
   Aynı kök neden `flutter analyze`'ı da çökertiyor (çıkış kodu 255), bu da
   `scripts/release_check.ps1` release kapısını geçilemez hale getiriyor.
2. **targetSdkVersion 35** — Play Console'un 31 Ağustos 2026 tarihli 36 gerekliliğini
   karşılamıyor. **27 gün kaldı.**

Ayrıca performans tarafında bir **gerçek bellek sızıntısı** (sınırsız marker ikon önbelleği)
ve haritayı gereksiz yere tam yeniden çizen bir yeniden-inşa zinciri tespit edildi.

**Önemli çerçeve düzeltmesi:** "6.000+ istasyonun harita render performansı" endişesi
ölçümle karşılığını bulmadı — harita hiçbir zaman 6.000 marker çizmiyor. Ayrıntı §2.1'de.

---

## 1. Release Konfigürasyonu ve API Güncellemesi

### 🔴 B1 — Release pipeline'ı tamamen bloke: ASCII olmayan proje yolu

Ölçüm (çalıştırıldı, tahmin değil):

```
$ flutter build appbundle --release
> Failed to apply plugin 'com.android.internal.application'.
   > Your project path contains non-ASCII characters. This will most likely
     cause the build to fail on Windows. Please move your project to a
     different directory.
Gradle task bundleRelease failed with exit code 1

$ flutter analyze   → LASTEXITCODE = 255   (analysis server çöküyor)
$ dart analyze      → LASTEXITCODE = 0     (74 info)
```

`flutter analyze` çöküşünün sebebi kod değil: analiz sunucusunun LSP `Content-Length`
başlığı `Masaüstü`'ndeki çok baytlı karakterlerde bayt/karakter uzunluğunu şaşırıyor
(`FormatException: Unexpected end of input`).

Bunun release'e etkisi zincirleme:

- `scripts/release_check.ps1:74` → `flutter analyze` çalıştırıyor → 255 → `Invoke-Step`
  fırlatıyor → **release kapısı hiçbir zaman tamamlanamıyor.**
- `scripts/release_check.ps1:94` → `flutter build appbundle` → AGP reddi.
- Depodaki `build/app/outputs/bundle/release/app-release.aab` **31 Temmuz tarihli, 58 MB** —
  yani mevcut kod tabanını temsil etmiyor, bayat bir artefakt.

**Öneri:** Projeyi ASCII bir yola taşımak (ör. `C:\dev\Fullet`). Bu hem AGP reddini hem de
`flutter analyze` çöküşünü tek hamlede çözer.
Alternatif olan `android.overridePathCheck=true` yalnızca AGP kontrolünü susturur —
`flutter analyze`'ı düzeltmez ve Windows'ta bilinen build kırılganlığını yerinde bırakır.
Bunu **önermiyorum**.

### 🔴 B2 — targetSdkVersion 35 → 36 (son tarih 31 Ağustos 2026)

`fullet_flutter/android/app/build.gradle`:

| Ayar | Şu an | Gereken |
|---|---|---|
| `compileSdkVersion` | 36 | 36 ✅ zaten uygun |
| `targetSdkVersion` | **35** | **36** |
| `minSdkVersion` | 21 | (karar gerekiyor — aşağıda) |

Bu tek satırlık bir değişiklik **değil**. Üç bağlı risk var:

**(a) Araç zinciri API 36 için eski.**
AGP 8.2.1 (`settings.gradle:17`), Gradle 8.7, Kotlin 1.9.22. compileSdk 36 zaten resmi
destek penceresinin dışında; targetSdk 36 ile birlikte AGP 8.6+ gerekiyor.

**(b) Flutter aracı zorunlu bir migrasyon dayatıyor — ve `minSdkVersion`'ı sessizce yükseltiyor.**
Build denemesi sırasında Flutter aracı `build.gradle` ve `gradle.properties` dosyalarını
kendiliğinden değiştirdi (bu değişiklikler denetim kapsamı dışı olduğu için **geri alındı**,
ağaç temiz):

```diff
-        minSdkVersion 21
+        minSdkVersion flutter.minSdkVersion     # = 24 (Flutter 3.44.8'de doğrulandı)

+android.builtInKotlin=false
+android.newDsl=false
```

`minSdkVersion 21 → 24` bir **ürün kararıdır, teknik detay değil**: Android 5.0 ve 5.1
cihazlar uygulamayı kaybeder. Bu kararın bilinçli verilmesi gerekiyor.

**(c) En yüksek regresyon riski: Android 16 zorunlu edge-to-edge.**
targetSdk 36'da edge-to-edge'den çıkış (opt-out) kaldırıldı. Kod tabanında ilgili yerler:

- `main.dart:26-32` ve `114-127` → `systemNavigationBarColor` set ediyor; API 35+'te bu no-op.
- `modern_map_screen.dart:1782-1786` → `StationBottomSheet` `Positioned(bottom: 0)` ile
  yerleştirilmiş; sistem navigasyon çubuğunun altında kalabilir.
- `modern_map_screen.dart:1622` → üst çubuk `MediaQuery.padding.top` kullanıyor ✅ (bu taraf doğru).

Bu, targetSdk yükseltmesinin **cihazda görsel doğrulama** gerektiren kısmı.

### 🟡 Sürüm kodu / adı

`pubspec.yaml: 1.0.2+5` ve `android/local.properties: versionCode=5`. Yeni yayın için
artırım gerekiyor. Git geçmişi versionCode 4'ün Play Console'da zaten kullanıldığını
gösteriyor (`7fce7b7`), yani 5 de yayınlanmışsa **6**'ya çıkılmalı — Play Console'dan
teyit edilmeli.

### 🟢 Debug bayrakları — temiz

- `debugShowCheckedModeBanner: false` ✅ (`main.dart:100`)
- `usesCleartextTraffic="false"` ✅
- `.env` `.gitignore`'da, depoda izlenmiyor ✅
- Release imzalama `key.properties` üzerinden koşullu ✅
- debug/profile manifest'leri yalnızca INTERNET izni içeriyor ✅

### 🟡 L4/L5 — Küçültme ve sembol gizleme kapalı

`buildTypes.release` içinde `minifyEnabled` / `shrinkResources` yok; release_check.ps1
`--obfuscate --split-debug-info` kullanmıyor. Dart kodu AOT derlendiği için asıl mantık
zaten korunuyor; etki paket boyutunda (AAB 58 MB). Bloklayıcı değil, isteğe bağlı iyileştirme.

### 🟡 L3 — `android.enableJetifier=true`

AndroidX-only bir projede gereksiz; build süresini uzatıyor. Kaldırılabilir.

### 🔵 Doğrulanması gereken (bulgu değil)

Google Maps API anahtarı `AndroidManifest.xml`'de açık. Bu Android Maps SDK için
**normaldir** — anahtar her hâlükârda APK'dan çıkarılabilir; korumayı Cloud Console'daki
paket adı + SHA-1 kısıtlaması sağlar. Commit `ddcbde6` ("yeni kısıtlı anahtarla değiştir")
bunun yapıldığını gösteriyor. Yayın öncesi kısıtlamanın hâlâ aktif olduğu teyit edilmeli.

---

## 2. Performans ve Stabilite

### 2.1 "6.000+ istasyon render performansı" — ölçüm sonucu

**Harita hiçbir zaman 6.000 marker çizmiyor.** İki katmanlı bir tavan var ve doğru çalışıyor:

- Ağ katmanı: `_maxResultsForZoom()` (`modern_map_screen.dart:880`) → zoom'a göre 120–260 kayıt.
- Çizim katmanı: `_declutterConfigForZoom()` (`:850`) → **en fazla 110 marker**; zoom < 11 ve
  25'ten fazla istasyonda hücre bazlı kümelemeye (`_clustersForZoom`) düşüyor.

Yani render hattı sınırlı ve sağlıklı. 6.000 istasyonun tamamı yalnızca
`SupabaseService._allStationsCache` içinde (arama + fiyat alarmları için) tutuluyor.
Gerçek performans riski render'da değil, aşağıdaki üç yerde.

### 🔴 H1 — Sınırsız marker ikon önbelleği (gerçek bellek sızıntısı)

`utils/marker_icon_factory.dart:7`

```dart
static final Map<String, BitmapDescriptor> _cache = {};
```

Hiçbir yerde temizlenmiyor, boyut sınırı yok, eviction yok. Önbellek anahtarı (`:20-21`)
**fiyat metnini ve durum bayraklarını** içeriyor:

```dart
'price|$brand|$priceText|$hasPrice|$priceStatus|$isCheapest|$isMostLogical|$compact|$isSelected|$isLowPriority'
```

Bu kombinasyonların hepsi oturum boyunca değişir: fiyatlar güncellenir, kullanıcı hareket
ettikçe `isCheapest`/`isMostLogical` tacı istasyon değiştirir, `isSelected` her dokunuşta
yeni bir 1.32x ölçekli PNG üretir. Her giriş çözülmüş bir `BitmapDescriptor` (124×60,
seçiliyken 164×79 PNG).

En kötü senaryo **sürüş modu**: `_handleDrivingPosition` (`:538`) her konum güncellemesinde
tam marker yeniden inşası tetikliyor, 45 saniyede bir de yeni bölge çekiliyor. Uzun bir
yolculukta önbellek monoton büyür.

**Öneri:** LRU sınırı (ör. 300 giriş) veya fiyat metnini anahtardan çıkarıp metni ayrı
katmanda çizmek.

### 🟠 H2 — `_markersNotifier` dispose edilmiyor

`modern_map_screen.dart:68` tanımlı, `dispose()` (`:928-935`) içinde yok. Aynı metotta
`_authSubscription`, `_fetchDebouncer`, `_markerDebouncer`, `_drivingPositionSubscription`
ve `_mapController` düzgün temizleniyor — yalnızca bu atlanmış.

### 🟠 H3 — Her tercih değişiminde haritanın tamamı yeniden inşa ediliyor

Zincir:

1. `build()` içinde `context.watch<UserPreferencesProvider>()` (`:1536`) → State provider'a bağımlı.
2. `didChangeDependencies()` (`:938`) → `_updateCalculationsAndMarkers(forceMarkerRefresh: true)`.
3. Bu da `SmartStationService.calculateBestStations` (tüm istasyonlar) + `_buildMarkers()`
   (110 ikon üretimi / önbellek araması + `Future.wait` + yeni `Set`).

`notifyListeners()` çağıran **her şey** bunu tetikliyor: `toggleFavoriteStation`,
`rememberStation`, `setSelectedFuel`, `updateTankCapacity`, `updateFuelConsumption`,
`mergeRemoteFavorites`, `clearVehicle`. Yani favoriye eklemek bile tüm haritayı yeniden çiziyor.

**Üstüne çift iş var:**

- `_selectStation` (`:1399`) → `prefs.rememberStation` (→ zincir) **ve ayrıca** kendi
  `unawaited(_buildMarkers())` çağrısı (`:1414`). İstasyona her dokunuşta en az iki tam inşa.
- Yakıt çipi (`:963-967`) → `prefs.setSelectedFuel` (→ zincir) **ve ayrıca** açık
  `_updateCalculationsAndMarkers(forceMarkerRefresh: true)`.

### 🟠 H4 — Async hatalar Crashlytics'e ulaşmıyor

`main.dart:38` yalnızca şunu kuruyor:

```dart
FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterFatalError;
```

`PlatformDispatcher.instance.onError` **kurulmamış**. Bu, Flutter widget ağacı dışındaki
yakalanmamış async hataların (Future zincirleri, platform kanalı hataları) hiçbir zaman
raporlanmadığı anlamına geliyor — crash görünürlüğünde kör nokta.

Buna karşılık `SupabaseService._reportSilently` (`:19-27`) yutulan hataları bilinçli olarak
Crashlytics'e non-fatal kaydediyor ✅ — bu tasarım doğru.

### 🟡 `_allStationsCache` kalıcı bellekte tutuluyor

`supabase_service.dart:30`. 5 dakikalık TTL yalnızca *yenilemeyi* kontrol ediyor; süre
dolduğunda bellek **boşaltılmıyor**, yeni veri gelene kadar eski liste duruyor. ~6.000
`Station` nesnesi + fiyatları + istasyon başına 20 fiyat geçmişi satırı, uygulama ömrü
boyunca statik alanda kalıyor. Sızıntı değil (sınırlı), ama sabit ve küçümsenmeyecek bir
bellek tabanı.

### 🟢 Hata yakalama — genel olarak sağlam

`_getLocation()` dört kademeli fallback ile pes etmiyor (`:202-285`); `fetchStations`
RPC → legacy → tablo → önbellek zinciriyle korunuyor; `_stationFetchSerial` /
`_markerBuildSerial` ile yarış koşulları engellenmiş; `mounted` kontrolleri tutarlı.
`dotenv` ve Firebase init hataları beyaz ekran yerine anlamlı ekrana düşüyor (`main.dart:44-67`).

---

## 3. Mantıksal Kontroller (UI/UX, Arama, Filtreleme)

### 🟠 M1 — Arama sonuçları sıralamadan ÖNCE 50'ye kırpılıyor

`modern_map_screen.dart:2469-2471`

```dart
} else if (filtered.length > 50) {
  filtered = filtered.sublist(0, 50);
}
```

`filtered`, önbelleğin döndürdüğü **veritabanı sırasında** — mesafe bu noktada henüz
hesaplanmadı (hesap `:2473-2486`'da, sıralama `:2488`'de). Yani "Shell" araması ülke
genelindeki ilk 50 Shell kaydını alıp *sonra* mesafeye göre sıralıyor.

**Kullanıcıya etkisi:** Kullanıcının 2 km ötesindeki Shell, bu ilk 50'ye girmediyse arama
sonuçlarında hiç görünmez — üstelik sonuç listesi "en yakın" gibi sıralanmış göründüğü için
eksiklik fark edilmez. Yaygın markalarda (Shell, Opet, PO — envanterde binlerce kayıt)
sistematik olarak tetiklenir.

**Düzeltme:** Önce mesafeyi hesapla ve sırala, kırpmayı en sona al.

### 🟡 M2 — Her tuş vuruşunda ~6.000 istasyon yeniden normalize ediliyor

`:2457-2459` her istasyon için 4 alanı birleştirip `normalizeTurkish()` çağırıyor; bu
fonksiyon 7 ardışık `replaceAll` yapıyor (`text_normalize.dart:13-25`). Tuş başına kabaca
**42.000 string işlemi, UI thread'inde** (250 ms debounce var ama işin kendisi ana iş
parçacığında).

Ayrıca sıralama karşılaştırıcısının içinde tekrar normalize ediliyor (`:2490-2493`) — sort
başına O(n log n) kez, aynı stringler için.

**Düzeltme:** Normalize edilmiş haystack'i `Station` üzerinde bir kez hesaplayıp saklamak.

### 🟡 M3 — Bayat hata banner'ı temizlenmiyor

`SupabaseService.lastStationFetchError` bazı **başarı** yollarında `null`'a çekilmiyor —
özellikle `_fetchStationsFromTableFallback` (`:152-184`) başarıyla dönerken bu alana
dokunmuyor. `_fetchStationsForRegion` (`:358`) bu alanı `_stationLoadError`'a kopyalıyor ve
`_statusMessage` (`:1113`) onu ilk sırada gösteriyor.

**Sonuç:** Bir istek hata verip sonraki istek fallback ile başarılı olursa, harita dolu
istasyonlarla çalışırken ekranda "Veri alınamadı" + "Tekrar dene" banner'ı asılı kalır.

### 🟡 M4 — Sistem teması değişince harita stili güncellenmiyor

`_currentIsDark` (`:91-95`) doğrudan `platformDispatcher.platformBrightness` okuyor, ancak
kod tabanında **hiçbir yerde** `WidgetsBindingObserver` / `didChangePlatformBrightness` yok
(lib genelinde 0 eşleşme — doğrulandı). `setMapStyle` yalnızca `onMapCreated` (`:1566`) ve
manuel geçiş düğmesinde (`:1694`) çağrılıyor.

Uygulama açıkken sistem teması değiştiğinde harita zemini eski stilinde kalır.

İkinci bir tutarsızlık: manuel geçiş `_isDarkModeOverride`'ı set ediyor (`:1689`) ama
**asla `null`'a döndürmüyor** → o andan itibaren sistem teması kalıcı olarak yok sayılıyor.
Üstelik bu tercih `SharedPreferences`'a yazılmadığı için uygulama yeniden başlatıldığında
sıfırlanıyor. Yani seçim ne oturum içinde geri alınabiliyor ne de kalıcı.

### 🟢 Doğrulandı, sorun yok

- `_stationsWithFuel` (`:399`) `&&` operatörü ile doğru süzüyor; testle korunuyor
  (`station_model_test.dart` "S2-1: yakit filtresi gercekten suzuyor").
- `MapFocusMode` tam bağlı — `ful_side_menu.dart:711-750` → `onFocusModeChanged` →
  `:1755-1762`. Ölü kod **değil**.
- Türkçe `İ` normalizasyonu doğru çözülmüş (`text_normalize.dart`), 5 testle korunuyor.
- Fiyat havuzu tutarlılığı (S2-2): marker'ın gösterdiği fiyat ile taç aynı havuzdan
  (`station.dart:120-136`), testlerle korunuyor.
- `_priceSortedResults` (`:2512`) `hasDisplayablePriceFor` ile süzüyor, bayat fiyat taze
  fiyattan ucuz görünemiyor.

---

## 4. Ölü ve Kirli Kod Analizi

Bu başlık **büyük ölçüde temiz çıktı**. Ölçümler:

| Kontrol | Sonuç |
|---|---|
| Statik analiz (`dart analyze`) | 74 bulgu, **hepsi `info`** — 0 warning, 0 error |
| Kullanılmayan private üye/alan | **0** (analyzer warning üretirdi) |
| TODO / FIXME / HACK / XXX | **0** (Dart + Python) |
| Yoruma alınmış kod bloğu | **0** |
| Çıplak `print()` | **0** |
| `kDebugMode` kullanımı | 0 |
| Hardcoded secret (py/supabase/admin_panel) | **0** |
| Çıplak `except:` (Python) | **0** |
| Flutter testleri | **33/33 geçiyor** |

### 🟡 M5 — `debugPrint` release build'de log yazıyor

20 çağrı (`supabase_service.dart` 11, `main.dart` 2, diğerleri 7). Yaygın yanılgının aksine
**`debugPrint` release derlemesinde elenmez** — logcat'e yazmaya devam eder. Supabase hata
mesajları ve marka fallback logları (`[Brand] RPC brand_filter returned 0 rows...`) üretim
cihazlarının logunda görünür.

**Öneri:** `if (kDebugMode)` sarmalayıcısı veya tek bir `_log()` yardımcısına toplamak.

### 🟡 L1 — `google_maps_cluster_manager_2` fiilen ölü bağımlılık

`pubspec.yaml`'da bildirilmiş, ancak tüm kod tabanında tek kullanımı `station.dart:4`
import'u ve `class Station with ClusterItem` mixin'i. `ClusterManager` sınıfı hiç
kullanılmıyor — kümeleme elle yazılmış (`_clustersForZoom`, `:823`). Mixin yalnızca
`location` getter'ı için duruyor, o da 3 satırlık bir ifade.

### 🟡 L2 — 74 deprecation

73 × `Color.withOpacity` → `.withValues()`; 1 × `Switch.activeColor` → `activeThumbColor`
(`settings_sheet.dart:473`). Hiçbiri build'i kırmıyor, ama gelecek Flutter sürümlerinde
kırılma adayı. `flutter_lints` sürümü de eski (`^2.0.0`; güncel seri 6.x) — modern lint
kuralları hiç uygulanmıyor.

### 🟡 L6 — `main.dart:105` build içinde Future oluşturuyor

`future: _getInitialScreen()` her `build()` çağrısında yeni bir Future üretir. `FulletApp`
pratikte nadiren yeniden inşa edildiği için şu an zararsız, ama anti-pattern.

### 🔵 Ölü sanılıp doğrulanan (dokunulmamalı)

- `win32: ^5.5.4` — hiçbir dosyada import edilmiyor **ama ölü değil**: `package_info_plus`
  üzerinden gelen transitive bağımlılığı sabitlemek için bilinçli konmuş, pubspec'te
  gerekçesi yazılı.
- `_fetchStationsByBrandsWholeCountry` / `_fetchStationsLegacy` — kullanılmıyor gibi
  duruyor ama gerçek hata fallback'leri, zincirin parçası.

---

## 5. Önerilen Uygulama Sırası

**Faz A — Yayını açan (bloklayıcı)**
1. B1: Projeyi ASCII yola taşı → `flutter analyze` ve `flutter build` çalışır hale gelir.
2. B2: AGP/Gradle/Kotlin yükselt → `targetSdkVersion 36`.
3. B2(b): `minSdkVersion 21 → 24` kararını **onayla** (Android 5.x cihaz kaybı).
4. B2(c): Edge-to-edge'i cihazda doğrula (bottom sheet + navigasyon çubuğu).
5. versionCode'u Play Console'a göre artır.

**Faz B — Stabilite / performans**
6. H1: Marker ikon önbelleğine LRU sınırı.
7. H4: `PlatformDispatcher.instance.onError` → Crashlytics.
8. H2: `_markersNotifier.dispose()`.
9. H3: `didChangeDependencies` zincirini daralt + çift `_buildMarkers()` çağrılarını kaldır.

**Faz C — Mantık düzeltmeleri**
10. M1: Arama kırpmasını sıralamadan sonraya al. *(kullanıcıya doğrudan yansıyan tek mantık hatası)*
11. M3: `lastStationFetchError`'ı başarı yollarında temizle.
12. M4: Tema değişimini dinle + override'ı kalıcılaştır/sıfırlanabilir yap.
13. M2: Arama normalizasyonunu önbellekle.

**Faz D — Temizlik (isteğe bağlı, yayın sonrasına ertelenebilir)**
14. M5: `debugPrint` → `kDebugMode` koruması.
15. L1: `google_maps_cluster_manager_2` bağımlılığını kaldır.
16. L2: `withOpacity` → `withValues` (74 nokta); `flutter_lints` güncelle.
17. L3/L4: `enableJetifier` kaldır; R8 + `--obfuscate` değerlendir.

---

## 6. Denetim Yöntemi ve Sınırları

**Çalıştırılan komutlar:** `dart analyze` (74 info), `flutter test` (33/33),
`flutter analyze` (255 — çöküş), `flutter build appbundle --release` (AGP reddi),
`git status/diff`, hedefli `grep` taramaları.

**Not:** `flutter build` denemesi sırasında Flutter aracı `android/app/build.gradle` ve
`android/gradle.properties` dosyalarını kendiliğinden değiştirdi. Bu değişiklikler denetim
kapsamı dışında olduğu için `git checkout` ile **geri alındı**; çalışma ağacı şu an temiz.
İçerikleri §1/B2(b)'de kayıt altına alındı — Faz A'da bilinçli olarak yeniden uygulanacak.

**Kapsanmayan:** Gerçek cihazda çalışma zamanı profillemesi (FPS, gerçek bellek grafiği)
yapılmadı — B1 nedeniyle build üretilemediği için mümkün değildi. H1/H3'ün etkisi kod
okumasıyla tespit edildi; büyüklüğü ancak build açıldıktan sonra DevTools ile ölçülebilir.
iOS tarafı kapsam dışıdır (projede `ios/` dizini yok). Backend (`scraper/`) yalnızca
güvenlik/hijyen açısından tarandı; iş mantığı denetimi bu raporun kapsamı değil.


---
---

# ═══ BÖLÜM B ═══ Tam Kod Denetimi ve Düzeltme Yol Haritası

*(kaynak: `FULLET_KOD_SAGLIGI_YOL_HARITASI.md` — Faz 0–3, 3 Ağustos 2026'da kapatıldı)*

---

# FULLET — TAM KOD DENETİMİ VE DÜZELTME YOL HARİTASI

**Tarih:** 2 Ağustos 2026
**Kapsam:** Tüm depo — 30 Python dosyası, 27 Dart dosyası, admin panel (React), 25 SQL
dosyası, 2 Edge Function, 2 GitHub Actions workflow'u. Satır satır okundu.
**Amaç:** "Uygulama yanlış fiyat gösteriyor ve taze veri çekemiyor" şikâyetinin
koddaki her kaynağını bulmak ve düzeltme sırasını belirlemek.

---

## 0. YÖNETİCİ ÖZETİ

Şikâyet tek bir hatadan gelmiyor. **Dört bağımsız arıza zinciri** aynı anda çalışıyor ve
her biri diğerini gizliyor:

| # | Zincir | Sonuç |
|---|---|---|
| A | Botlar hatayı yutup `exit 0` dönüyor + CI'da alarm bayrağı kapalı | Kırık parser "başarılı" görünüyor |
| B | `son_guncelleme` kolonu iki farklı anlam taşıyor + eşikler çakışıyor | Fiyat doğruyken bile "bayat" oluyor |
| C | Sabit kolon indeksleri + çapraz doğrulama kapısı yok | Yanlış fiyat sessizce yazılıyor (Shell LPG) |
| D | Uygulamada yakıt filtresi ölü + tazelik göstergesi yanlış | Kullanıcı "Yok"/eski fiyat görüyor |

**En önemli tek cümle:** Bu sistemde hiçbir bileşen "veri kötü" diyemiyor. Bot 0 kayıt
yazınca `success`, panel 72 saati temiz sayarken uygulama 12 saati bayat sayıyor,
`ops_report` Shell alarmlarını körü körüne kapatıyor, `quarantine_old_prices.py` hiç
çalışmıyor. Gözlem katmanı yalan söylediği için 4 marka aylardır sessizce ölü.

Toplam **26 doğrulanmış bulgu**. Aşağıda önem sırasına göre, sonra düzeltme sırası.

---

## 1. BULGULAR

### S0 — SİSTEMİK KÖK NEDENLER
*(Tek düzeltme, çok belirti kapatır. Diğer her şeyden önce bunlar.)*

---

#### S0-1 — Her fiyat botu istisnayı yutup başarıyla çıkıyor
**Dosyalar:** `scraper/opet_bot.py:56`, `po_bot.py:60`, `bp_bot.py:60`,
`aytemiz_bot.py:66`, `tp_bot.py:118`, `total_bot.py:65`, `shell_bot.py:207`,
`shell_station_bot.py:175`, `total_station_bot.py:60`, `tp_station_bot.py:46`

Her botun kalıbı aynı:

```python
except Exception as exc:
    print(f"[WARN] Opet scrape failed: {exc}")
return scraped_data          # ← boş liste

if __name__ == "__main__":
    data = scrape_opet_data()
    save_to_supabase(data, default_brand="Opet")   # 0 kayıt yazar
    print("[OK] Opet finished")                     # exit code 0
```

Site şeması değişse, HTTP 500 dönse, JSON bozulsa — bot **`exit 0`** ile biter.
`run_all_bots._run_subprocess_once` yalnızca `returncode`'a bakar (satır 130), dolayısıyla
`bot_runs.status = 'success'`, `exit_code = 0` yazılır.

> Karar protokolündeki "7 markanın 4'ünde tek bir taze fiyat yok ama botlar `success`"
> gözleminin doğrudan mekanizması budur.

**İstisna:** `news_bot.py:131` — tek doğru davranan bot, `raise SystemExit(1)` yapıyor.
Diğerleri onu örnek almalı.

---

#### S0-2 — CI, tüm hata/alarm altyapısını kapatıyor
**Dosya:** `.github/workflows/otopilot.yml:159`

```yaml
FULLET_FAIL_ON_BOT_ERROR: "0"
```

Bu tek satır şunları etkisizleştiriyor:

- `run_all_bots.should_open_failure_alert()` → her zaman `False` → **hiçbir bot için
  `system_alerts` kaydı açılmıyor.**
- `run_all_bots.main()` → `failures` dolu olsa bile `return 0` (satır 256-259).
- Son commit'te eklenen retry + `TOLERATED_FAILURE_BOTS = set()` temizliği
  (satır 47, 170-177) **üretimde hiç çalışmıyor** — o kod yolu CI'da erişilemez.

Geriye tek alarm yolu kalıyor: `telemetry._check_consecutive_failures`. O da S3-2'deki
hata yüzünden güvenilmez.

---

#### S0-3 — `son_guncelleme` iki farklı anlam taşıyor; eşikler birbirini yiyor
**Dosyalar:** `scraper/database_writes.py:66-80`, `database/auto_price_staleness.sql:27-36`,
`database/production_hardening.sql:309-338`

Üç yer aynı kolona farklı anlam yüklüyor:

1. **Trigger** (`log_fiyat_degisimi`, BEFORE UPDATE): `son_guncelleme`'yi yalnızca
   **fiyat değerinin değiştiği** anda `NOW()` yapıyor → "son değişim zamanı".
2. **pg_cron JOB 1**: `son_guncelleme < NOW() - 12 hours` ise `fresh → stale` →
   "son doğrulama zamanı" varsayıyor.
3. **Bot diff'i** (`_bulk_upsert_prices`): fiyat aynı + status `fresh` + yaş **< 24 saat**
   ise satırı tamamen atlıyor → `son_guncelleme` **bump edilmiyor.**

Sonuç, Türkiye'de fiyatların ayda birkaç kez değiştiği gerçeğiyle birleşince:

```
T+0h   bot yazar        → fresh,  son_guncelleme = T0
T+6h   bot koşar        → fiyat aynı, fresh, yaş 6h < 24h → ATLA (bump yok)
T+12h  cron             → stale                              ← fiyat DOĞRU ama bayat
T+18h  bot koşar        → status != fresh → yazar → fresh
T+24h  ...              → döngü tekrar
```

Fiyat hiç değişmese bile sistem sürekli `fresh → stale → fresh` salınıyor. Kullanıcı
gün içinde **doğru fiyatı "⚠️ Bayat fiyat" bandıyla** görüyor.

`scraper/test_backend_utils.py:226` (`test_zero_cost_unchanged_prices_skipped`) bu atlama
davranışını *istenen davranış* olarak test ediyor — optimizasyon fikri doğru, ama 24 saatlik
eşik 12 saatlik cron'la uyumsuz. **Asıl eksik, ayrı bir "son doğrulama" kolonu.**

---

#### S0-4 — Dört bileşen, dört farklı tazelik eşiği
| Bileşen | Dosya | Eşik |
|---|---|---|
| pg_cron `fresh→stale` | `auto_price_staleness.sql:34` | **12 saat** |
| pg_cron `stale→unknown` | `auto_price_staleness.sql:50` | **48 saat** |
| `quarantine_old_prices.py` | satır 42 | **72 saat** |
| `ops_report.py` | `MAX_PRICE_AGE_HOURS` satır 54 | **48 saat** |
| Admin panel | `admin_panel/src/App.jsx:16` | **72 saat** |
| `backend_health_check.py` (haber) | satır 25-26 | 24/48 saat |

Admin panel 72 saati "Temiz" gösterirken uygulama aynı fiyata "Bayat" diyor.
**"Panel yeşil, veri ölü" tablosunun ikinci yarısı budur.**

---

### S1 — YANLIŞ VERİ ÜRETENLER

---

#### S1-1 — Shell LPG sabit kolon hatası (HÂLÂ AÇIK)
**Dosya:** `scraper/shell_bot.py:128`

```python
"LPG": _price_at(cols, 12) or _price_at(cols, 10),
```

Son commit Shell'i tolere listesinden çıkardı ama **kolon hatası düzeltilmedi.**
Canlı veri: Shell LPG 37,74 TL, diğer markalar ~31,3 TL (%20 sapma, 860 kayıt).

Aynı fonksiyonda `Kursunsuz 95` ve `Motorin` de `or` fallback kullanıyor (satır 126-127) —
aynı sınıf hataya açık, şu an tesadüfen doğru okuyorlar.

---

#### S1-2 — Aynı sayfa, iki botta farklı kolon indeksleri
**Dosyalar:** `scraper/po_bot.py:44-48` vs `scraper/bp_bot.py:44-48`

Her ikisi de `petrolofisi.com.tr` üzerinde aynı tablo yapısını okuyor
(`soup.select("table tr")`), ama:

| | Kurşunsuz 95 | Motorin | LPG |
|---|---|---|---|
| `po_bot.py` | `cols[1]` | **`cols[2]`** | **`cols[6]`** |
| `bp_bot.py` | `cols[1]` | **`cols[3]`** | **`cols[8]`** |

İkisi aynı anda doğru olamaz. BP botu %19 taze veri üretirken PO botunun %0 üretmesi
bu tutarsızlıkla uyumlu. **Canlı sayfadan doğrulanmalı** — ama asıl çözüm sabit indeks
değil, başlık metnine göre kolon bulma (S1-4).

> ### ⚠️ DÜZELTME (2 Ağustos, Faz 1) — bu bulgu YANLIŞTI
>
> Canlı sayfalar çekildi. İki sayfa **farklı kolon sayısına** sahip ve her iki bot
> da kendi tablosu için **doğru** indeksleri kullanıyordu:
>
> ```
> PO: Şehir | V/Max Kurşunsuz 95 | V/Max Diesel | Gazyağı | Kalorifer | Fuel Oil | PO/gaz Otogaz
>            [1] ✓                 [2] ✓                                           [6] ✓
> BP: Şehir | BP Kurşunsuz | BP Ultimate | BP Diesel | BP Ultimate Diesel | ... | Otogaz | Y.K.Fuel Oil
>            [1] ✓                         [3] ✓                                 [8] ✓
> ```
>
> Aynı şekilde Aytemiz'in `price_start=6` sabiti ve TP'nin indeksleri de doğruydu.
> **Tek gerçek veri bozan kolon hatası Shell LPG'ydi (S1-1).**
>
> Yine de beşi de başlık tabanlı çözüme taşındı: sabit indeks doğru olsa bile
> kırılgandır — Shell'de tam olarak bu yüzden patladı.
>
> **Ders:** "İki bot aynı sayfayı farklı okuyor" çıkarımı, sayfaların aynı olduğu
> **varsayımına** dayanıyordu. Kaynağı görmeden yapılan çıkarım yanıltıcıydı;
> raporda "canlı doğrulanmalı" işareti bu yüzden konmuştu.

---

#### S1-3 — Aytemiz parser'ı sihirli sayılarla token yürüyor
**Dosya:** `scraper/aytemiz_bot.py:15-33`

```python
price_start = 6
index = price_start
while index + 5 < len(tokens):
    ...
    index += 6
```

Tablo düzeni değişirse (ki `veri_kaynagi` olarak bildirilen URL ile gerçekte
çekilen URL bile farklı — satır 42 `/benzin-fiyatlari`, satır 64 `akaryakit-fiyatlari`),
bu döngü sessizce yanlış hücreleri okur ya da hiç sonuç üretmez. Ayrıca
`index + 5 < len(tokens)` koşulu **son satırı her zaman düşürüyor.**

---

#### S1-4 — Çapraz doğrulama kapısı yok; fiyat aralığı çok geniş
**Dosyalar:** `scraper/normalization.py:88,111`, `scraper/backend_health_check.py:229-231`

`parse_price` `0 < price < 300` kabul ediyor. LPG ~31, motorin ~82 olan bir pazarda
bu, kolon kayması sonucu okunan neredeyse her sayıyı geçerli sayar. Shell LPG'nin 37,74
olarak yazılması tam olarak buradan geçti.

`backend_health_check.py` daha dar bir aralık (5–200) kullanıyor ama o da 37,74'ü yakalayamaz.
**Hiçbir yerde "bu markanın bu yakıttaki medyanı, diğer markaların medyanından ne kadar
sapıyor" kontrolü yok.** Tek satırlık bu kural hatayı ilk gün yakalardı.

---

#### S1-5 — `quarantine_old_prices.py` üretimde hiç çalışmıyor
**Dosya:** `scraper/run_all_bots.py:247-251`

```python
subprocess.run(
    [sys.executable, str(SCRAPER_DIR / "quarantine_old_prices.py")],
    cwd=SCRAPER_DIR,
    env=bot_env,          # ← bot_env = {"FULLET_PUSH_SUMMARY": "0"}
)
```

`env=bot_env` ortamı **değiştirmiyor, tamamen değiştiriyor.** Alt sürece yalnızca
`FULLET_PUSH_SUMMARY` geçiyor; `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
`FULLET_ALLOW_DB_WRITE`, hatta `PATH` yok. Script satır 29'da
`FULLET_ALLOW_DB_WRITE != "1"` görüp `return 1` ile çıkıyor — ve dönüş kodu
**kontrol bile edilmiyor.**

Aynı dosyadaki `_run_subprocess_once` bunu doğru yapıyor (satır 91-93:
`env = os.environ.copy(); env.update(...)`). Sadece bu çağrı atlanmış.

---

#### S1-6 — Bölgesel eşleştirme, normalize edilmemiş kolonla sorguluyor
**Dosya:** `scraper/matching.py:52-63`

```python
supabase.table("istasyonlar").select(...).eq("marka", brand).eq("il", city)
```

`city`, `normalize_city()` çıktısı (`"ISTANBUL"`, ASCII, büyük harf). DB'deki `il`
değeri istasyon envanteri botlarından geldiği için genelde aynı formatta — ama
`_load_brand_stations` (satır 267-270) aynı işi **Python tarafında normalize ederek**
yapıyor. İki farklı eşleştirme stratejisi aynı veriye uygulanıyor:

- `save_to_supabase` → `_station_targets` → **ham SQL eşitliği**
- `save_regional_prices_to_supabase` → `_load_brand_stations` → **normalize edilmiş eşleşme**

Opet/PO/BP/Aytemiz birinci yolu, TP/Total/Shell ikinciyi kullanıyor. Tek bir
eşleştirme yolu olmalı — ve DB'deki tek bir kayıtta bile Türkçe karakter varsa
birinci yol sessizce 0 hedef döndürür (fiyat hiçbir yere yazılmaz, hata da vermez).

Ayrıca `_regional_targets_from_loaded:289` ilçe eşleşmesini `district in
clean_text(...)` **alt dize** kontrolüyle yapıyor — `"MERKEZ"` gibi bir değer çok
sayıda yanlış ilçeyi eşleştirir.

---

#### S1-7 — `normalize_fuel` Türkçe "ş" harfini tanımıyor
**Dosya:** `scraper/normalization.py:63-81`

```python
text = clean_text(value).lower()      # "kurşunsuz 95" (ş korunuyor)
if "kursunsuz" in text or "benzin" in text or "95" in text:   # ← "kurşunsuz" eşleşmez
```

`clean_text` NFKC normalize ediyor ama harf çevirisi yapmıyor. `"kurşunsuz"` metni
yalnızca sondaki `"95" in text` fallback'i sayesinde doğru sınıflanıyor. Kaynak "95"
yazmayı bırakırsa (örn. "Kurşunsuz Benzin V/Max") sınıflama sessizce bozulur.
`CITY_REPLACEMENTS` burada da uygulanmalı.

---

### S2 — UYGULAMADA YANLIŞ GÖSTERİM

---

#### S2-1 — Yakıt filtresi tamamen ölü (❗ en görünür kullanıcı hatası)
**Dosya:** `fullet_flutter/lib/screens/modern_map_screen.dart:390-396`

```dart
List<Station> _stationsWithFuel(String fuelType) {
  return _stations
      .where((station) =>
          station.hasDisplayablePriceFor(fuelType) || station.isVisibleInApp)
      .toList(growable: false);
}
```

`_stations` listesi `SupabaseService._parseStations` içinde (satır 424) **zaten**
`isVisibleInApp == true` süzgecinden geçmiş. Yani `|| station.isVisibleInApp` her
zaman `true` → **koşulun tamamı her istasyon için doğru** → yakıt filtresi hiç
çalışmıyor.

Kullanıcı LPG'ye basınca LPG satmayan istasyonlar da haritada kalıyor ve
`formatMarkerPrice` onlara **"Yok"** yazıyor. `||` yerine `&&` olmalı (ya da yalnızca
`hasDisplayablePriceFor`).

Bu hata üç ayrı yerden yayılıyor:
- `_filteredStations` → harita marker'ları ve boş-durum kartı (satır 1714)
- `_drivingTargetStation` (satır 432) → sürüş banner'ında "`— TL`" gösteriyor (satır 1188)
- `_buildEmptyState` neredeyse hiç tetiklenmiyor — kullanıcı "fiyat yok" mesajı yerine
  "Yok" dolu bir harita görüyor

---

#### S2-2 — Marker fiyatı bayat, "en ucuz" tacı taze: harita kendiyle çelişiyor
**Dosya:** `modern_map_screen.dart:689-706`

```dart
final priceNum       = station.priceValueFor(selectedFuel);        // stale DAHİL
final trustedPriceNum = station.trustedPriceValueFor(selectedFuel); // yalnızca fresh
final isCheapest = trustedPriceNum != null && ... ;
```

Marker etiketi bayat fiyatı gösteriyor, ama "en ucuz"/"en mantıklı" rozeti yalnızca
taze fiyatlar arasından seçiliyor. Fiyatların %79'u bayat/bilinmiyor olduğu için
**kullanıcı ekranda 79,50 yazan bir marker görürken, mavi "en ucuz" rozeti 82,10 yazan
başka bir istasyonda duruyor.** Aynı çelişki `SmartStationService` (satır 48, 93),
`_StationCluster.minPriceFor` (satır 2137) ve `_stationsForZoom` (satır 783) için de geçerli.

Karar tek olmalı: ya bayat fiyat haritada hiç gösterilmez, ya da akıllı hesap da bayatı
(açık bir güven düşüşü etiketiyle) hesaba katar. Şu anki karışım en kötü seçenek.

---

#### S2-3 — "Güncel" etiketi yalan söyleyebiliyor
**Dosya:** `fullet_flutter/lib/models/station.dart:151-159, 178-197`

```dart
DateTime? get latestPriceUpdatedAt {
  final candidates = [
    ...prices.map((price) => price.updatedAt).whereType<DateTime>(),
    if (dataUpdatedAt != null) dataUpdatedAt!,     // ← istasyon satırının zamanı
  ];
  ...
}
```

`dataUpdatedAt` = `istasyonlar.guncellenme_tarihi`. Bu kolon `matching._station_targets`
tarafından **her bot koşusunda**, fiyat yazılmasa bile güncelleniyor (satır 74-79, 148-158).
Sonuç: fiyat üç haftalık olsa bile `getLastPriceChangeText()` "Güncel" ya da "2s önce"
diyebiliyor.

İlgili: `getLastPriceChangeText()` (satır 178) `priceHistory`'yi **yakıt tipine bakmadan**
tarıyor — motorin değişimini LPG kartında "3s önce" olarak gösterebilir.

---

#### S2-4 — Arama, Türkçe "İ" harfinde kırılıyor
**Dosya:** `modern_map_screen.dart:2535-2544`

```dart
String _normalize(String value) {
  return value.toLowerCase()
      .replaceAll('ı', 'i').replaceAll('ğ', 'g') ... ;   // 'İ' listede yok
}
```

Dart'ta `'İ'.toLowerCase()` → `'i' + U+0307` (birleşen nokta). `İSMAİL PETROL` →
`"i̇smai̇l petrol"`; kullanıcının yazdığı `"ismail"` bu dizede **bulunmaz.**
`brand_utils._normalizeBrandText` bu harfi ele alıyor, `_normalize` almıyor.

> **DÜZELTME (Faz 2, canlı doğrulama) — BU BULGU YANLIŞTI.**
> Dart 3.12.2'de `'İ'.toLowerCase()` **tek karakter** `'i'` (U+0069) döndürüyor;
> birleşen nokta üretilmiyor. Ölçüldü: `'İ'.codeUnits == [304]`,
> `'İ'.toLowerCase().codeUnits == [105]`. Eski `_normalize` `İSMAİL PETROL`'ü
> zaten `"ismail petrol"` yapıyordu ve `"ismail"` araması **çalışıyordu.**
> Canlı veride de sorun yok: `istasyonlar`ın 3.433 satırının **0**'ı birleşen
> nokta içeriyor, hepsi NFC; 933 isimde `İ` var ve hepsi doğru eşleşiyor.
>
> Yine de yapılan değişiklik korundu, ama **hata düzeltmesi olarak değil**:
> iki ayrı normalleştirici (`_normalize` + `_normalizeBrandText`) tek
> `utils/text_normalize.dart`'a indirildi. `_normalizeBrandText` içindeki
> `replaceAll('İ','i')` satırı `toLowerCase()`'ten sonra geldiği için zaten
> **ölü koddu** — silindi. U+0307 temizliği savunma amaçlı duruyor ve
> `text_normalize_test.dart` Dart tam Unicode eşlemesine geçerse düşecek
> şekilde davranışı kilitliyor.
>
> Bu, S1-2'den sonra denetimin **ikinci** yanlış bulgusu. Ders aynı:
> mekanizma iddiası ölçülmeden düzeltme yazılmamalı.

---

#### S2-5 — `fuelMatches` fazla gevşek
**Dosya:** `fullet_flutter/lib/utils/price_formatter.dart:48-72`

`source.contains(target) || target.contains(source)` ve `elektrik` için
`source.contains('ev')` — bugün 3 kanonik yakıt adıyla zararsız, ama `Elektrik`
devreye girdiğinde (EV pivotu senaryosu) yanlış eşleşme üretecek. Ayrıca
`Station.priceFor` **ilk eşleşmeyi** döndürüyor; bir istasyonda hem `Motorin` hem
`Motorin Ultra` satırı olsa hangisinin gösterileceği rastlantısal.

---

#### S2-6 — Fiyat alarmı zaman damgası yerel saatle yazılıyor
**Dosya:** `fullet_flutter/lib/services/price_alert_service.dart:84-85`

```dart
await ...update({'son_tetiklenme': now.toIso8601String()}).eq('id', alert.id);
```

`DateTime.now()` yerel saat, `toIso8601String()` offset yazmıyor. Postgres bunu UTC
olarak yorumluyor → Türkiye'de **3 saatlik kayma**. 24 saatlik tekrar-bildirim
koruması (satır 67-70) bu yüzden 21 saatte açılıyor. `toUtc()` gerekli.

---

### S3 — SESSİZ / ÖLÜ MEKANİZMALAR

---

#### S3-1 — `ops_report` Shell alarmlarını körü körüne kapatıyor
**Dosya:** `scraper/ops_report.py:216-217`

```python
resolve_system_alerts(source="bot:shell_bot.py")
resolve_system_alerts(source="bot:shell_station_bot.py")
```

Rapor temizse — ki eşikler istasyon *sayısına* bakıyor, fiyat *tazeliğine* değil —
Shell botunun gerçekten patlamış olup olmadığına bakılmaksızın alarmları kapatıyor.
"Tolere edilen bot" döneminden kalma; son commit tolere listesini boşalttı ama
bu iki satır kaldı. **Shell'in kalıcı arızası hâlâ görünmez.**

---

#### S3-2 — Ardışık hata sayacı mevcut koşuyu iki kez sayıyor
**Dosya:** `scraper/telemetry.py:42-53, 83-90`

`record_bot_run` önce satırı **insert ediyor** (satır 42), sonra
`_check_consecutive_failures` çağrılıyor (satır 62). Orada:

```python
# Mevcut çalışmayı (henüz insert edilmedi) dahil et      ← yorum yanlış
statuses = [current_status] + [r.get("status") for r in recent]
```

`recent` sorgusu az önce yazılan satırı zaten içeriyor. Tek bir hata
`consecutive_failures = 2` üretiyor → `critical` alarm ilk hatada patlıyor.
Alarm yorgunluğu; gerçek ardışık hatalar sıradanlaşıyor.

---

#### S3-3 — `low_priority` düşürme işi hiçbir şey yapmıyor
**Dosyalar:** `database/auto_price_staleness.sql:59-76`, `models/station.dart:89-90`

pg_cron JOB 3, 7 gündür güncellenmemiş istasyonları `visible → low_priority`'ye
düşürüyor. Ama uygulamada:

```dart
bool get isVisibleInApp =>
    visibilityStatus == 'visible' || visibilityStatus == 'low_priority';
```

`low_priority` da gösteriliyor, RPC de (`create_postgis_rpc.sql:34`) her ikisini
kabul ediyor. **Güvenlik mekanizması kurulmuş ama hiçbir yere bağlanmamış.**

---

#### S3-4 — Push token temizliği aktif kullanıcıların token'ını siliyor
**Dosya:** `database/auto_price_staleness.sql:79-89`

Yorum "90 günde hiç **kullanılmamış** token'ları sil" diyor, kod
`olusturulma_tarihi < NOW() - 90 days` yazıyor. `son_guncelleme` kolonu tam bu iş için
var (`rls_policies.sql:10`) ama kullanılmıyor. 90 günlük sadık kullanıcı push almayı
kesiyor.

---

#### S3-5 — Push altyapısı uçtan uca kopuk
**Dosyalar:** `supabase/functions/fiyat-push/index.ts:88-101`, `services/notification_service.dart`

- Edge function yalnızca **Expo** token'larına gönderiyor; FCM token'ları sayılıp
  `pendingFcm` olarak raporlanıyor, **gönderilmiyor** (satır 96-104).
- Flutter uygulaması `firebase_messaging` kullanmıyor ve `push_tokens` tablosuna
  **hiç yazmıyor** — depoda tek bir `push_tokens` insert'i yok.
- Yani `send_summary_push` her koşuda çağrılabilir ama hiçbir cihaza ulaşmaz.

Ölü kod değil, **ölü ürün yüzeyi** — ya tamamlanmalı ya da kaldırılmalı.

---

#### S3-6 — `get_nearby_stations` dört ayrı dosyada tanımlı
**Dosyalar:**
- `database/create_postgis_rpc.sql` (5 argüman)
- `supabase/migrations/20260505195000_production_hardening.sql:304` (4 argüman)
- `supabase/migrations/20260708120100_...:15` (4 argüman + GRANT 4 arg)
- `supabase/migrations/20260708130000_...:20` (5 argüman)

Migration'lar sırayla uygulanınca son durum doğru. Ama `database/*.sql` scriptleri
elle çalıştırılan **ikinci bir doğruluk kaynağı.** Biri `supabase db push` yaptıktan
sonra `database/create_postgis_rpc.sql`'i (veya tersini) çalıştırırsa iki overload
birlikte kalabilir → PostgREST çağrıyı çözemez → uygulama sessizce
`_fetchStationsByBrandsWholeCountry` fallback'ine düşer (2.617 istasyonu telefonda
sayfalayarak tarar).

`supabase_service.dart`'taki üç katmanlı savunmacı fallback zinciri (satır 87-95,
216-229, 283-292) bu belirsizliğin ürünü.

---

#### S3-7 — Testler var, CI'da hiç koşmuyor
**Dosyalar:** `.github/workflows/otopilot.yml`, `.github/workflows/admin-panel-pages.yml`

13 Flutter testi (`test/*.dart`) ve 20 Python testi (`scraper/test_*.py`) mevcut —
`test_shell_bot.py` bile Shell'in motorin kolonunu doğruluyor. **Hiçbir workflow
`pytest` ya da `flutter test` çalıştırmıyor.** `scripts/release_check.ps1` yerel,
elle çalıştırılan bir script.

`test_zero_cost_unchanged_prices_skipped` gibi testler doğru davranışı kilitliyor
ama kimse çalıştırmıyor.

---

#### S3-8 — `main.dart` başlangıçta çökebilir
**Dosya:** `fullet_flutter/lib/main.dart:40`

```dart
await dotenv.load(fileName: '.env');    // try/catch yok
```

`.env` asset'i eksikse `dotenv.load` **fırlatır** ve `runApp` hiç çağrılmaz →
kullanıcı beyaz ekran görür. Hemen altındaki `_ConfigurationErrorApp` (satır 44-50)
yalnızca "yüklendi ama boş" durumunu yakalıyor — asıl riskli durumu değil.
`.env` `pubspec.yaml:40`'ta asset olarak listelenmiş ama `.gitignore`'da; herhangi bir
temiz checkout + build bu tuzağa düşebilir.

---

#### S3-9 — Sürüm numarası üç yerde elle yazılmış
**Dosyalar:** `services/app_heartbeat_service.dart:11`, `modern_map_screen.dart:1355`,
`modern_map_screen.dart:1752` → hepsi `'1.0.2'`; `pubspec.yaml:4` → `1.0.2+5`.

Kohort analizini `app_heartbeats.app_version` üzerinden yapıyorsunuz. Sürüm
yükseltilip bu üç sabit unutulursa **retention verisi sessizce yanlış kohorta yazılır.**
`package_info_plus` ile tek kaynaktan okunmalı.

---

#### S3-10 — Hata yutma politikası tutarsız
**Dosya:** `services/supabase_service.dart`

`upsertUserProfile:444` → `catch (_) {}` (tamamen sessiz),
`addFavorite:478` / `removeFavorite:488` → sessiz,
`getUserFavorites:464` → sessizce `{}` döndürüyor,
ama `deleteUserData:451` bilinçli olarak yutmuyor (yorumu da var).

Favori ekleme sunucuda başarısız olursa kullanıcı yerelde favorilenmiş görüyor,
başka cihazda göremiyor — ve hiçbir yerde iz kalmıyor.

---

#### S3-11 — Diğer küçük bulgular

| Dosya:satır | Bulgu |
|---|---|
| `matching.py:175` | `inserted.data[0]["id"]` — insert boş dönerse `IndexError`; yalnızca çağıranın `try` bloğunda `skipped++` olarak yutulur |
| `database_writes.py:97-99` | `veri_kaynagi` fallback'i istisna **metnine** bakıyor (`if "veri_kaynagi" not in str(exc)`) — kırılgan |
| `db_utils.py:233-251` | `CANONICAL_FUELS` içindeki `"Elektrik"` her koşuda "unknown" yazma denemesi üretiyor (gereksiz yazma trafiği) |
| `backend_health_check.py:231` | Geçerli yakıt listesi `("Kursunsuz 95","Motorin","LPG")` — `Elektrik` eklenirse sağlık kontrolü kırmızıya döner |
| `shell_bot.py:95` | `int(os.environ.get("SHELL_MAX_TARGETS_PER_RUN", 150))` — geçersiz değer `ValueError` ile botu düşürür |
| `modern_map_screen.dart:1570` | `onCameraIdle` her seferinde `_scheduleMarkerRefresh(force: true)` → tüm marker ikonları yeniden çiziliyor |
| `station.dart:193-196` | `_relativeTime`, sunucu saati ileriyse negatif farkı "Güncel" sayıyor |

---

## 2. YOL HARİTASI

Sıralamanın tek bir mantığı var: **önce ölçüm aletini onar, sonra veriyi, en son
görüntüyü.** Kirli aletle yapılan her düzeltme doğrulanamaz.

---

### FAZ 0 — GÖRÜŞ AÇ (yarım gün) — *diğer her şeyin önkoşulu*

Şu an hiçbir düzeltmenin işe yarayıp yaramadığını göremezsiniz. Önce bunu çözün.

1. **`FULLET_FAIL_ON_BOT_ERROR: "0"` satırını kaldır** (`otopilot.yml:159`).
   → Retry + alarm altyapısı canlanır. *(S0-2)*
2. **Botlara dürüst çıkış kodu ver.** Her bot dosyasının `__main__` bloğuna:
   scrape 0 kayıt döndürdüyse veya istisna yakalandıysa `raise SystemExit(1)`.
   `news_bot.py:131` kalıbını kopyalayın. *(S0-1)*
3. **`bot_runs`'a `records_written` kolonu ekle.** `SaveSummary` zaten
   `stations_touched`/`prices_touched` taşıyor — bot bunu stdout'a basıp
   `run_all_bots` telemetriye yazsın. 0 ise `status='empty'` + alarm.
4. **`ops_report.py:216-217`'deki iki `resolve_system_alerts` satırını sil.** *(S3-1)*
5. **`telemetry._check_consecutive_failures` çift saymasını düzelt** — ya insert'ten
   önce çağır, ya `recent`'ten mevcut koşuyu çıkar. *(S3-2)*
6. **CI'ya test adımı ekle:** `pytest scraper/` + `flutter test`. Mevcut 33 test zaten
   yazılmış durumda. *(S3-7)*

**Doğrulama:** Bir botun URL'sini kasten bozun. Beklenen: workflow kırmızı,
`system_alerts`'ta kayıt, `bot_runs.status != 'success'`.

---

### FAZ 1 — VERİ HATTINI DÜZELT (2–3 gün)

Faz 0 olmadan bu fazın hiçbir adımı doğrulanamaz.

7. **`quarantine_old_prices.py` env hatasını düzelt** — `env=bot_env` yerine
   `os.environ.copy()` + update; dönüş kodunu kontrol et. *(S1-5)*
   → Tek satırlık düzeltme, muhtemelen aylardır çalışmayan bir bakım işini geri getirir.
8. **`son_dogrulama` (last_verified_at) kolonunu ekle.** *(S0-3 — en yüksek değerli düzeltme)*
   - `fiyatlar`'a yeni `TIMESTAMPTZ` kolon.
   - Botlar fiyat değişmese de **her doğrulamada** bu kolonu bump etsin
     (`_bulk_upsert_prices` atlama optimizasyonu korunur — sadece bu kolon yazılır).
   - pg_cron JOB 1/2 `son_guncelleme` yerine `son_dogrulama`'ya baksın.
   - `son_guncelleme` yalnızca "son fiyat değişimi" anlamında kalsın (trigger zaten öyle davranıyor).
9. **Tazelik eşiklerini tek yerden yönet.** *(S0-4)* Kaynak: `fresh ≤ 12h`,
   `stale ≤ 48h`, sonrası `unknown`. Admin panelin 72'sini, `quarantine_old_prices`'ın
   72'sini, `ops_report`'un 48'ini bu tek tanıma bağlayın.
10. **Kolon eşlemesini başlık metnine bağla.** *(S1-1, S1-2, S1-3)*
    Ortak bir `resolve_columns(header_row) -> {fuel: index}` yardımcısı yazın;
    `normalization.normalize_fuel` zaten "lpg"/"otogaz"/"motorin" metnini tanıyor.
    Uygulama sırası: `shell_bot` → `po_bot` → `bp_bot` → `aytemiz_bot` → `tp_bot`.
    Sabit indeks kalan hiçbir bot bırakmayın.
11. **Çapraz doğrulama kapısı ekle.** *(S1-4)* Yazmadan önce: bir markanın bir yakıttaki
    medyanı, diğer markaların medyanından **%10'dan fazla** saparsa → yazma, `system_alerts`'a
    `critical` düş. Bu kural tek başına Shell LPG'yi ilk gün yakalardı.
12. **Eşleştirmeyi tekilleştir.** *(S1-6)* `_station_targets`'ın ham SQL eşitliğini
    `_load_brand_stations`'ın normalize eden yoluna taşıyın; ilçe eşleşmesini alt dize
    yerine tam eşleşmeye çevirin.
13. **`normalize_fuel`'e `CITY_REPLACEMENTS` uygula.** *(S1-7)* Üç satır.

**Doğrulama (kapı):** Faz 1 sonunda `ops_report.py` 7 markanın **hepsinde** taze fiyat
görmeli ve marka-yakıt medyanları %10 bandı içinde olmalı. Olmuyorsa Faz 2'ye geçmeyin.

---

### FAZ 2 — UYGULAMADAKİ YALANI KES (1–2 gün)

Veri düzeldikten sonra görüntüyü düzeltin — tersi sırada neyin düzeldiğini ayırt edemezsiniz.

14. ✅ **`_stationsWithFuel`'deki `||`'ı `&&` yap.** *(S2-1)* Tek karakter, en görünür
    kullanıcı hatasını kapatır. Sonrasında boş-durum kartı gerçekten çalışmaya başlar.
15. ✅ **Bayat fiyat politikasını netleştir ve tek yerde uygula.** *(S2-2)*
    Önerim: bayat fiyat haritada gösterilsin **ama** marker'da görsel olarak ayrışsın
    (zaten `marker_icon_factory.dart:86` turuncu paleti var) **ve** "en ucuz"/"en mantıklı"
    hesabı da aynı havuzu kullansın. Şu anki iki farklı havuz kabul edilemez.
    → Uygulandı: `Station.priceValueFor` tek havuz (fresh+stale, unknown hariç);
    `SmartStationService` (2 yer), marker tacı, `_stationsForZoom`, `minPriceFor`
    hepsi buna bağlandı. Eşit fiyatta taze olan tacı alır. `trustedPriceValueFor`
    yalnızca **fiyat alarmında** kaldı (bildirim göndermenin eşiği gösterimden yüksek).
16. ✅ **`latestPriceUpdatedAt`'ten `dataUpdatedAt`'i çıkar.** *(S2-3)* İstasyon satırının
    güncellenme zamanı fiyat tazeliği değildir. `getLastPriceChangeText`'i yakıt tipine
    duyarlı hale getirin.
    → Ayrıca `station_bottom_sheet.dart`'taki `?? station.dataUpdatedAt` geri düşüşü
    kaldırıldı; asıl "Güncel" yalanı **orada** görünüyordu (`getLastPriceChangeText`'in
    hiç çağrılmadığı ortaya çıktı).
17. ⚠️ **`_normalize`'a `'İ'` çevirisini ekle** (`toLowerCase` öncesi). *(S2-4)*
    → **Bulgu yanlıştı** (bkz. S2-4 düzeltme notu). Hata yoktu; değişiklik
    normalleştirici birleştirmesi olarak korundu.
18. ✅ **`son_tetiklenme`'yi `toUtc()` ile yaz.** *(S2-6)*
19. ✅ **`dotenv.load`'ı try/catch'e al**, hata durumunda `_ConfigurationErrorApp`. *(S3-8)*
    → Yalnızca `load`'ı sarmalamak YETMİYOR: `dotenv.env` getter'ı da
    `NotInitializedError` fırlatıyor (flutter_dotenv 6.0.1, `dotenv.dart:39`),
    yani çökme bir satır aşağı kayardı. `dotenv.isInitialized` kontrolü eklendi.
20. ✅ **Sürüm numarasını `package_info_plus`'tan oku**, üç sabiti sil. *(S3-9)*
    → `utils/app_version.dart` tek kaynak; `main()` içinde `AppVersion.init()`
    heartbeat'ten ÖNCE çağrılıyor. Yan etki: `package_info_plus` `win32`'yi
    `<6.0.0` serbest bıraktığı için çözümleyici 5.2.0'ı seçti; o sürüm Dart
    3.4'te kaldırılan `UnmodifiableUint8ListView`'i kullanıyor ve `flutter test`
    derlemesini kırıyordu. `win32: ^5.5.4` sabitlendi, `sdk` alt sınırı
    gerçeği yansıtacak şekilde `>=3.3.0` yapıldı.

---

### FAZ 0–2 DENETİMİ (3 Ağustos 2026) — kapatılan boşluklar

Faz 0/1/2 tamamlandıktan sonra yapılan gözden geçirme, üretim verisiyle
doğrulanan **dört yeni bulgu** çıkardı. Hepsi düzeltildi.

#### D1 — Hedef kapsaması ölçülmüyordu (Faz 0'ın kapatmadığı boşluk) ❗
Faz 0 yalnızca *"bot HİÇ kayıt üretmedi mi?"* sorusunu görünür kıldı
(`empty`). *"Bot hedeflerinin çoğunu kaybetti mi?"* sorusu sorulmuyordu.

Canlı `bot_runs.stdout_excerpt` üzerinden 8 koşu sayıldı — sonuç her koşuda
neredeyse aynı:

| Koşu | Denenen hedef | `Element is not visible` | Grid okundu |
|---|---|---|---|
| 02 Ağu 16:24 | 42 | 27 | 11 |
| 02 Ağu 11:01 | 45 | 27 | 13 |
| 02 Ağu 06:23 | 44 | 29 | 10 |
| 01 Ağu 22:18 | 40 | 34 | 5 |

**Shell hedeflerinin ~%63'ünü her koşuda sessizce kaybediyordu** ve yine
yüzlerce kayıt döndürdüğü için `success` görünüyordu. Sonuç canlıda:
Shell'in 1.152 fiyat satırının %26'sı taze, %36'sı **bayat**, %38'i
bilinmiyor — diğer altı markada bayat **sıfır**.

*Kök neden:* `page.locator(...).click(force=True)` + sabit
`wait_for_timeout(750)`. DevExpress combobox'ı grid callback'i sürerken
DOM'da kalıyor ama görünmez oluyor; `force` **görünürlük kontrolünü
atlamaz**, dolayısıyla Playwright fırlatıyor ve hedef `except` tarafından
yutuluyordu.

*Düzeltme:* sabit uyku yerine görünürlük bekleme (`_settle` + `wait_for`),
hedef başına bir kez retry, ve kapsama muhasebesi:
`[RECORDS] ... targets_ok=A targets_total=B` →
`run_all_bots` → yeni **`degraded`** bot_runs durumu + `warning` alarmı
(eşik: `db_utils.MIN_TARGET_COVERAGE` = %70).
`degraded` pipeline'ı kırmızıya döndürmez — kısmi veri doğrudur ve exit 1
9 dakikalık kazımayı boşuna tekrarlardı. Migration:
`database/add_bot_runs_degraded_status.sql` (canlıya uygulandı).

#### D2 — Çapraz doğrulama kapısı, koruduğu veriyi siliyordu ❗
`save_to_supabase` / `save_regional_prices_to_supabase` sonunda
"bu koşuda raporlanmayan yakıtları `unknown` yap" süpürgesi çalışıyor.
Kapı bir yakıtı reddedince o yakıt öğelerden düşüyor, süpürge de onu
"raporlanmadı" sayıp **mevcut sağlam fiyatları `unknown`'a çeviriyordu.**
Yani Faz 1'de eklenen güvenlik mekanizması, tek bir hatalı koşuda o markanın
o yakıttaki tüm geçmişini silebilirdi. `apply_sanity_gate` artık reddedilen
yakıt kümesini çağırana döndürüyor ve o yakıtlar süpürgeden muaf tutuluyor.

#### D3 — Faz 2'nin 18/19/20. maddeleri (yukarıda işaretlendi)

#### D4 — "İLÇE/İL" birleşik `il` değerleri
20 istasyonun `il` kolonu `MERAM/KONYA` biçimindeydi ve `_station_targets`
`.eq("il","KONYA")` sorguladığı için **20'sinin de taze fiyatı yoktu.**
`normalization.split_province_district` / `normalize_province` eklendi
(81 il listesine bakar, konuma değil) ve ingest + okuma yollarına bağlandı;
`database/repair_composite_province_values.sql` mevcut satırları onardı
(18/20 taşındı, distinct `il` 119 → 108). Kalan 2 satır `unique_isim_ilce`
kısıtına takılıyor ve **kopya değil** — koordinatları hedeflerinden 2,4 km
ve 3,5 km uzakta, yani ayrı gerçek istasyonlar. Asıl kusur kısıtta: `isim`
bu markalarda marka adı olduğu için aynı ilçedeki iki Petrol Ofisi şemada
temsil edilemiyor. Kısıtı değiştirmek istasyon kimliği/dedupe mantığını
etkilediğinden ayrı bir karar olarak bırakıldı.

#### Doğrulanıp REDDEDİLEN bulgu — madde 12 (S1-6, eşleştirmeyi tekilleştir)
Yol haritası "DB'de Türkçe karakter varsa `_station_targets` sessizce 0 hedef
döndürür" diyordu. Canlı ölçüm bunu **çürüttü**: Türkçe `ilce` içeren 234
istasyonun **%96,2'sinin** taze fiyatı var; ASCII olanlarda bu oran %52,6.
Sebep: bu yolu kullanan botlar (Opet/PO/BP/Aytemiz) **il düzeyinde** fiyat
yazıyor, `item["ilce"]` boş, dolayısıyla `ilike("ilce", ...)` filtresi hiç
çalışmıyor. Madde 12'nin gerekçesi mevcut bot bileşiminde geçerli değil;
eşleştirmeyi tekilleştirmek 1.100+ istasyonun çalışan yazma yolunu riske
atacağı için **yapılmadı**. Bu, denetimin **üçüncü** yanlış bulgusu
(S1-2 ve S2-4'ten sonra) — ders yine aynı: mekanizma iddiası ölçülmeden
düzeltme yazılmamalı.

---

### FAZ 0–2 DENETİMİ — KAPATILAN İKİ BULGU (3 Ağustos 2026, ikinci tur)

#### B1 — `degraded`, kritik "arka arkaya BAŞARISIZ" alarmına dönüşüyordu ❗
`telemetry.record_bot_run` `success/ok` olmayan **her** durumu hata sayıyor,
`_check_consecutive_failures` de geçmiş `degraded` satırlarını hata olarak
sayıp seriyi uzatıyordu. Üretimde fiilen patladı:

```
2026-08-02T23:11:19  warning   shell_bot.py hedeflerin çoğunu okuyamadı
2026-08-02T23:11:20  critical  shell_bot.py arka arkaya başarısız
```

23:00 ve 23:26'daki iki `degraded` koşu bu alarmı açtırdı — oysa bot her iki
koşuda da yüzlerce fiyat yazmıştı. `degraded` tasarım gereği "veri yazıldı ama
eksik" demek. `NON_FAILURE_STATUSES` eklendi; `degraded` artık seriyi kırar ve
eski hata alarmını kapatır (kapsama uyarısı farklı `title` ile açık kalır).
4 regresyon testi, biri gerçek hataların HÂLÂ eskale ettiğini korur.

#### B2 — Kapsama sayıları hiçbir yerde kalıcı değildi
`_compact_log` stdout'un **ilk** 4000 karakterini saklar; `[RECORDS] …
targets_ok=A targets_total=B` satırı ~150 hedeflik koşunun **sonunda** basılır.
Canlı kontrol: 20 `shell_bot` kaydının **hiçbirinde** kapsama satırı yok.
Kapsama yalnızca `system_alerts.metadata`'da ve yalnızca `degraded` koşular
için kalıyordu — başarılı koşuda %71 mi %100 mü olduğu, yani eşiğe doğru
**trend**, görülemiyordu. (İroni: D1 teşhisi tam da `stdout_excerpt` okunarak
yapılmıştı; düzeltmeden sonra o yöntem çalışmıyor.)
`bot_runs.targets_ok` / `targets_total` kolonları eklendi
(`database/add_bot_runs_target_coverage.sql`); kapsama artık `status`'ten
bağımsız olarak **her** koşuda yazılıyor.

---

### FAZ 3 (YENİDEN TANIMLANDI) — İSTASYON VERİSİ: TABAN ÖLÇÜMÜ

Kullanıcı Faz 3'ü "tüm Türkiye'deki istasyonların konumları, eksik ilçeler ve
kopya kayıtlar" olarak yeniden tanımladı. Aşağıdaki 21–25. maddeler
(ölü mekanizmalar) **ertelendi**.

**Taban ölçümü, canlı veri, 3 Ağustos 2026 — salt-okunur.**

Toplam **3.433** istasyon. (Hedef olarak anılan 12.000+ ile arada büyük fark
var; Türkiye'de ~13.000 istasyon olduğu düşünülürse kapsama ~%26. Bu bir
*temizlik* değil *toplama* işi — ayrı karar.)

**Kritik metodoloji notu:** ham sayılar felaket görünüyor ama neredeyse
tamamı **pasif** satırlardan geliyor. Uygulama yalnızca `aktif` istasyonları
gösterir:

| kusur | ham sayı | AKTİF içinde |
|---|---|---|
| `il` 81 il listesinde değil | 292 | **0** |
| koordinat yok | 182 | **0** |
| `veri_kaynagi` boş | 353 | **0** |
| `ilce` boş | 591 | 29 (%1,1 — ve %100 taze) |
| fiyat satırı yok | 584 | 142 |

**Aktif 2.636 istasyonun %98,9'u kusursuz.** 797 pasif satır 1.065 `unknown`
fiyat satırı taşıyor ve **sıfır** tazesi var — eski moloz, doğru şekilde
gizli. `aktif` bayrağı görevini yapıyor.

`normalize_province` bir **doğrulayıcı değil**, normalleştiricidir: tanımadığı
değeri aynen geri verir (`'BILINMIYOR' -> 'BILINMIYOR'`). Geçerlilik ölçümü
`PROVINCES` kümesine karşı yapılmalı.

#### Aktiflerde kalan gerçek kusurlar (Faz 3'ün asıl kapsamı)

**F3-1 — 100 aktif kopya çifti (<150m, aynı marka).**
98'inde **ikisinde de** fiyat var (bölünmüş veri); **6'sı aynı yakıtta farklı
fiyat gösteriyor** — kullanıcı aynı istasyonu haritada iki pinde iki fiyatla
görüyor (ör. DİYARBAKIR ÇEVRE YOLU: LPG 33,94 `fresh` / 38,51 `unknown`).
51 çift "jenerik marka adı" vs "gerçek isim". Kaynak dağılımı suçluyu
gösteriyor: **66x Shell'in fiyat botu kendisiyle**, 29x TotalEnergies API'si
kendisiyle. Yani sorun iki bot arasında değil, **dedupe anahtarında**:
`unique_isim_ilce` kısıtında `isim` bu markalarda marka adı olduğu için aynı
ilçedeki iki istasyon temsil edilemiyor — D4'te "ayrı karar" diye bırakılan
kısıt sorunu tam olarak budur.

**F3-2 — 142 aktif istasyonun hiç fiyat satırı yok.**
TotalEnergies 134, Türkiye Petrolleri 8. Hepsi *istasyon* botlarından geliyor
(`exapi/stations`, `tppd.com.tr/tr/stationmaplist`); fiyat botları bunları hiç
eşleştirmiyor. Uygulamada görünür ama kalıcı olarak fiyatsız.

**F3-3 — Shell tazeliği (kapasite).** 94 öncelikli + koşu başına 56 slot →
tam tur **8 koşu = 48 saat**, `fresh` penceresi 12 saat. Öncelikli olmayan bir
ilçe tasarım gereği zamanın ~%25'inde taze olabilir. Canlı doğrulama birebir:
öncelikli %62,6 taze / diğer **%20,3** taze, %57,7 bilinmiyor. Shell tüm
istasyonların %41'i. Son 24 saatteki 7 Shell koşusunun **3'ü `degraded`**.

---

### FAZ 3 — YAPILAN İŞ (3 Ağustos 2026)

#### F3-1 ✅ Kopya istasyonlar — üretim durduruldu, mevcutlar birleştirildi

*Kök neden:* `_station_inventory_coord_key` bir **kova** idi —
`(marka, il, ilce, round(lat,4), round(lon,4))`. `round(...,4)` ≈ 11 m, yani
aynı istasyonun 12 m farkla kaydedilmiş iki sürümü farklı kovalara düşüp
"ayrı istasyon" sayılıyordu. Anahtarda `il`/`ilce` de vardı; `ilce=''` vs
`ilce='ÇEKMEKÖY'` farkı tek başına kopya üretiyordu.

*Üretim tarafı:* `matching.StationProximityIndex` — 3×3 hücre komşuluğu
taranır (kova **sınırında** duran çiftler eski yöntemin asıl kırıldığı
yerdi), yarıçap 75 m, kimlik yalnızca marka + konum. Üç yazma yolu da
bağlandı.

*Yarıçap 75 m ölçümle seçildi* (101 canlı çift üzerinde): 0-75 m'de 78 çift
birleşir; 75-150 m'deki 18 çiftin **16'sı gerçekten ayrı istasyon**
(`YAĞLI BATI`/`YAĞLI DOĞU`, `POLATLI BATI`/`POLATLI DOĞU`,
`DAVUTPAŞA ALTYOL`/`DAVUTPAŞA ÜSTYOL`) — yol ayrımının iki yanı. Yarıçapı
topyekûn büyütmek bunları yanlışlıkla birleştirirdi.

*Mevcutlar:* `scraper/merge_duplicate_stations.py` (varsayılan dry-run).
İki kademe: ≤75 m isimden bağımsız, 75-150 m yalnızca biri jenerik isimliyse
(`'Shell'`, `'Total'` — fiyat botu artefaktı). **79 kopya silindi, 208 fiyat
hayatta kalanlara taşındı**, 5 kümede LPG çakışması vardı (hepsinde takılı
kalmış `38.51` `unknown` değeri), taze olan kazandı. Favoriler ve fiyat
alarmları silmeden **önce** taşınır — `ON DELETE CASCADE` yüzünden aksi hâlde
sessizce kaybolurlardı (bu koşuda 0 favori/0 alarm etkilendi).
**Doğrulandı:** 75 m içinde kalan kopya çifti 101 → **0**.

*Bilinen kalıntı:* `BAĞCILAR-2 (12T951)` ↔ `Total Bağcılar-2` (146 m) aynı
istasyon ama ikisi de tam jenerik değil; tek satır için bulanık isim
eşleştirmesi kırılgan olurdu, elle bırakıldı.

#### F3-2 ✅ 142 aktif ama kalıcı fiyatsız istasyon

*Kök neden:* markalar iki farklı granülerlikte fiyat yayınlıyor ve sistem
bunları eşitlemiyordu. Opet/PO/BP/Aytemiz **il** düzeyinde yazıyor (`ilce`
boş → ilçe filtresi hiç devreye girmiyor → o ildeki tüm istasyonlar fiyat
alıyor). TotalEnergies/TP ise **ilçe** düzeyinde yazıyor, dolayısıyla
`ilike("ilce", "%X%")` yalnızca beslemede adı geçen ilçeleri seçiyordu.
140 istasyonun 137'sinin **ili tutuyordu** — onları kesen ilçe filtresiydi.

*Çözüm:* tüm öğeler işlendikten **sonra** tek seferlik son geçiş; ilçesi
beslemede olmayan istasyona ilin medyan fiyatı yazılır. (Öğe başına
yapılsaydı her ilçe sırayla tüm eşleşmemiş istasyonları sahiplenip
birbirini ezerdi.)

*Neden güvenli — ölçüldü:* TotalEnergies canlı beslemesinde (944 satır) aynı
il içinde ilçeler arası Motorin farkı **medyan 0,02 TL**, 7 ilde tam sıfır;
tek anlamlı sapma K.MARAŞ (1,50 TL). Bu bir tahmin üretmek değil,
granülerlik farkını eşitlemek. En kritik garanti testle kilitli: **gerçek
ilçe fiyatı alan istasyona il medyanı yazılmaz.**

**Doğrulandı:** aktif ama fiyatsız istasyon 142 → **0**.

#### F3-3 ✅ Shell kapasitesi — hedef tavanı 150 → 250

Tam tur 48 saat → ~19 saat (fresh penceresi 12 saat). Destekleyici sabitler
birlikte taşındı, yoksa tavanı tek başına yükseltmek **her koşuyu
`degraded`** yapardı (payda büyür, pay bütçeyle kesilir): bütçe 1500→1700,
subprocess timeout 1800→2100, workflow 45→55 dk. 3 test aritmetiği kilitler.

#### Faz 3'te AÇIK kalanlar
* İstasyon **sayısı** 3.433 — hedef olarak anılan 12.000+ ile arada büyük
  fark var. Bu bir temizlik değil **toplama** işi (yeni istasyon kaynakları
  gerekir) ve ayrı bir karardır.
* 797 pasif satır + 1.065 `unknown` fiyat satırı: eski moloz, uygulamada
  görünmüyor. Temizliği düşük öncelikli.
* Eski Faz 3 maddeleri (21–25, ölü mekanizmalar) hâlâ ertelendi.

---

### FAZ 3 (ESKİ) — ÖLÜ MEKANİZMALARI KAPAT (yarım gün) — *ertelendi*

Bunlar bugün zarar vermiyor ama gelecekte yanlış güven üretir.

21. **`low_priority` kararını ver:** ya uygulamada gerçekten düşür (`isVisibleInApp`'ten
    çıkar veya marker'da soluklaştır), ya pg_cron JOB 3'ü kaldır. *(S3-3)*
22. **Push token temizliğini `son_guncelleme`'ye çevir.** *(S3-4)*
23. **Push altyapısına karar ver:** *(S3-5)* Kullanıcı sayısı 1 iken FCM entegrasyonu
    tamamlamak yanlış yatırım — **kaldırmayı öneriyorum.** `fiyat-push` fonksiyonu,
    `send_summary_push` çağrıları ve `push_tokens` tablosu ölü yüzey olarak kalırsa
    bir sonraki denetimde yine "çalışıyor mu?" diye zaman harcarsınız.
24. **SQL doğruluk kaynağını teke indir.** *(S3-6)* `database/*.sql` içindeki
    fonksiyon tanımlarını `supabase/migrations/`'a taşıyın; `database/` yalnızca
    tek seferlik onarım scriptleri için kalsın ve README'de bu net yazsın.
    `20260708120100` dosyası `20260708130000` tarafından tamamen eziliyor — süperseded
    olduğu dosya başına yazılmalı.
25. **`upsertUserProfile` / `addFavorite` / `removeFavorite`'ın sessiz `catch`'lerine
    en azından `debugPrint` + Crashlytics kaydı ekle.** *(S3-10)*

---

### FAZ 4 — REGRESYON KİLİDİ (yarım gün)

Bulunan her hata sınıfı için bir test. Bunlar olmadan aynı hatalar geri gelir.

- `shell_bot` / `po_bot` / `bp_bot` / `aytemiz_bot` için **başlık tabanlı kolon
  çözümleme testi** (kayıtlı HTML fixture ile).
- **Çapraz doğrulama kapısı testi:** %20 sapan bir marka medyanı yazmayı engelliyor mu?
- **Boş scrape testi:** bot 0 kayıt döndürdüğünde `SystemExit(1)` atıyor mu?
- **`_stationsWithFuel` testi:** LPG seçiliyken LPG'siz istasyon listede yok.
- **Tazelik testi:** `son_dogrulama` bump edilen bir fiyat 12 saat sonra hâlâ `fresh` mi?
- Hepsi CI'da (Faz 0, madde 6).

---

## 3. SIRALAMANIN GEREKÇESİ

**Neden Faz 0 önce?** Şu anda bir düzeltme yaptığınızda işe yarayıp yaramadığını
göremiyorsunuz — bot patlasa da yeşil, veri ölü olsa da yeşil. Aleti onarmadan
ölçüm yapılmaz. Faz 0 yarım gün ve geri kalan her şeyin doğrulanabilirliğini sağlar.

**Neden Shell LPG ilk sırada değil?** Çünkü tek başına düzeltilirse **aynı sınıftan
başka hataların olup olmadığını bilemezsiniz.** S1-2 (PO/BP kolon çelişkisi) tam da
bunu gösteriyor: Shell'e odaklanırken aynı hata iki bot daha yapıyor olabilir.
Faz 1'in 10. maddesi (başlık tabanlı eşleme) tüm sınıfı birden kapatır ve 11. madde
(çapraz doğrulama) bir daha olmasını engeller.

**Neden `son_dogrulama` bu kadar yukarıda?** Çünkü diğer tüm parser'ları düzeltseniz
bile bu kolon olmadan fiyatların önemli bir kısmı **doğruyken bayat görünmeye devam
edecek.** "Taze veri çekemiyor" şikâyetinin bir kısmı parser hatası değil, muhasebe hatası.

**Neden uygulama en sonda?** `&&` düzeltmesi (S2-1) tek karakterlik ve çok çekici —
ama önce yaparsanız, kullanıcı bu sefer "yakıt filtresi çalışıyor ama hepsi bayat"
görür. Veri hattı düzelmeden görüntü düzeltmek şikâyeti dönüştürür, çözmez.

---

## 4. KARAR PROTOKOLÜ İLE İLİŞKİ

`FULLET_KARAR_PROTOKOLU.md` Adım 1'de üç madde vardı; bu denetim onları genişletiyor:

| Karar protokolü maddesi | Bu yol haritasındaki karşılığı | Durum |
|---|---|---|
| Shell LPG kolonunu düzelt | Faz 1 / madde 10 | Genişletildi: 5 botun tamamı |
| Çapraz doğrulama kapısı ekle | Faz 1 / madde 11 | Aynen |
| Sessiz başarısızlığı bitir | Faz 0 / madde 1-3 | Genişletildi: CI bayrağı da dahil |
| Opet/PO/TP/Aytemiz neden yazmıyor? | S1-2, S1-5, S1-6 | **Cevaplandı** (aşağıda) |

**"4 bot neden hiç taze fiyat yazmıyor?" — CEVAP (2 Ağustos, canlı veriyle kesinleşti):**

Hipotezlerimden ikisi yanlıştı, biri doğruydu:

| Hipotez | Sonuç |
|---|---|
| Parser kırık, bot sessizce boş dönüyor (S0-1) | ❌ **Yanlış** — botlar çalışıyor ve yazıyordu |
| PO kolon indeksleri yanlış (S1-2) | ❌ **Yanlış** — indeksler doğruydu (yukarıdaki düzeltme) |
| Tazelik muhasebesi bozuk (S0-3) | ✅ **DOĞRU — tek ve yeterli sebep** |

Canlı `bot_runs` + `fiyatlar` zaman damgaları mekanizmayı birebir gösterdi:

```
01 Ağu 22:13  Opet/PO/Aytemiz/TP yazdı        -> fresh
02 Ağu 06:14  bot koştu, fiyat aynı, yaş 8s   -> diff ATLADI (doğrulama izi yok)
02 Ağu 10:14  pg_cron (12s eşiği)             -> stale      <- "0 taze fiyat"
02 Ağu 16:20  bir sonraki koşu                -> tekrar fresh
```

Yani dört marka **ölü değildi, salınıyordu.** Karar protokolündeki "%0 taze"
ölçümü, salınımın bayat evresinde alınmış bir anlık görüntüydü. BP ve
TotalEnergies'in aynı anda taze görünmesinin sebebi de fiyatlarının o koşuda
gerçekten değişmiş olmasıydı (değişen fiyat diff'i atlamaz).

**Faz 1 sonrası ölçüm (aynı gün, düzeltmelerden sonra):**

| Marka | Önce (taze) | Sonra (taze) | Bayat |
|---|---|---|---|
| TotalEnergies | %50,0 | **%89,6** | 0 |
| Opet | **%0,0** | **%87,7** | 0 |
| Petrol Ofisi | **%0,0** | **%47,2** | 0 |
| Aytemiz | **%0,0** | **%45,8** | 0 |
| Türkiye Petrolleri | **%0,0** | **%45,1** | 0 |
| BP | %19,0 | **%42,2** | 0 |

Altı markada da **bayat sayısı sıfır** — salınım tamamen durdu. Kalan `unknown`
satırlar meşru: o istasyonda satılmayan yakıtlar (LPG) ve hiç doldurulmamış
`Elektrik`. Doğrulama: `Kursunsuz 95` ve `Motorin` taze sayıları (1394), altı
botun yazdığı istasyon toplamıyla birebir eşleşiyor.

> Not: Karar protokolü "yeni özellik yok, yalnızca doğruluk borcu" diyordu. Bu yol
> haritasının tamamı o tanıma uyuyor — hiçbir maddede yeni kullanıcı özelliği yok.
> Faz 3'ün 23. maddesi (push'u kaldır) **yüzey azaltıyor**, artırmıyor.

---

## 5. TAHMİNİ SÜRE

| Faz | Süre | Kritiklik |
|---|---|---|
| Faz 0 — Görüş aç | 0,5 gün | Zorunlu önkoşul |
| Faz 1 — Veri hattı | 2–3 gün | Şikâyetin ana kaynağı |
| Faz 2 — Uygulama | 1–2 gün | Görünür kullanıcı hatası |
| Faz 3 — Ölü mekanizmalar | 0,5 gün | Gelecekteki yanlış güveni önler |
| Faz 4 — Regresyon kilidi | 0,5 gün | Kalıcılık |
| **Toplam** | **5–7 gün** | |

---

# BÜYÜK KAPANIŞ VE TEMİZLİK OPERASYONU (3 Ağustos 2026)

Kullanıcı Faz 0–3'ün kapanış onayını istedi. Onaydan **önce** yapılan ölçüm,
Faz 3'ün kapalı OLMADIĞINI gösterdi. Aşağıdaki operasyon o boşlukları kapattı
ve ertelenen 21–25. maddeleri bitirdi. (Uygulama planı `implementation_plan.md`
dosyasındaydı; Faz 4 tamamlandığı için 4 Ağustos 2026'da silindi — içeriği git
geçmişinde `243c866` ve öncesindeki commit'lerde duruyor.)

## Kapanışı engelleyen bulgular (ölçüldü)

### A1 — F3-1'in "101 kopya → 0" iddiası tutmuyordu ❗
Canlıda **26 aktif kopya çifti** vardı (`ÇİNÇİN.` ↔ `ÇİNÇİN.` **0,0 m**,
`MENEMEN ÇIKIŞI.` ↔ kendisi **0,0 m**). Hepsinin `olusturulma_tarihi` Nisan–Mayıs,
yani yeni üretilmiş değil — **birleştirmenin atladığı** kayıtlar.

*Kök neden (kanıtlandı):* `merge_duplicate_stations.py` yalnızca **aktif**
istasyonları kümeliyordu. Çiftin bir üyesi o an pasifse çift hiç görülmüyordu;
sonra fiyat yazma yolu (`istasyonlar.aktif = True`) o kaydı diriltince kopya
**aktif** olarak geri geliyordu. Kanıt: birleştirmeden sonra aktif istasyon
2.636 → 2.728, üstelik arada **79 kayıt silinmişken**. Değişmemiş scriptin
bugünkü dry-run'ı aynı kopyaları buluyor — tek değişen girdi aktif kümesiydi.

*Ders (dördüncü kez aynı ders):* düzeltme yazmadan önce ölç. Bu kez ölçüm
düzeltmeden önce yapıldı ve hipotez B0 adımında doğrulandı.

### A2 — 178 aktif ve görünür Shell istasyonunun hiç gösterilebilir fiyatı yoktu
Kullanıcı o pinlere basınca **"Yok"** görüyordu. Diğer altı markada bu sayı
sıfırdı. F3-3 (tavan 150→250) kapsamayı %85,6'ya çıkardı ama Shell'in ilçe
listesi 250'den uzun; kuyruktaki ilçeler sıraya gelmiyor.

### A3 — `aktif` ve `visibility_status` çelişiyordu
232 satır "aktif ama hidden", 354 satır "pasif ama visible". İki bayrak
bağımsız yazılıyordu, tutarlılık hiçbir yerde zorlanmıyordu.

### A4 — Envanter botu her koşuda istasyonları `low_priority`'ye düşürüyordu
`database_writes.py` koşulsuz `visibility_status: "low_priority"` yazıyordu;
fiyatı taze bir `visible` istasyon bile her envanter koşusunda düşüyordu.
Canlıda 1.052 satır bu durumdaydı.

### A5 — 9 sayfalamada `ORDER BY` yoktu
`ORDER BY`'sız sayfalama Postgres'te garantisizdir. **Hasar kanıtlanmadı**
(tek snapshot'ta kayıp yok), risk olarak kapatıldı.

### Bonus — canlı ile dosya arasında DRIFT (en tehlikeli bulgu) ❗
`database/auto_price_staleness.sql` canlıyla uyuşmuyordu: Faz 1'de pg_cron
JOB 1/2 canlıda `COALESCE(son_dogrulama, son_guncelleme)`ye çevrilmişti ama
dosya hâlâ `son_guncelleme` diyordu. Dosyayı iyi niyetle yeniden çalıştıran
biri **Faz 1'in en değerli düzeltmesini geri alır** ve fiyat salınımını geri
getirirdi. Bu, 24. maddenin (SQL doğruluk kaynağı) neden gerçek bir borç
olduğunun kanıtıdır.

## Yapılan iş

| Adım | İş | Sonuç |
|---|---|---|
| B0 | A1 kök nedenini ölç | Hipotez kanıtlandı |
| B1 | Üretimi durdur | Kopya üretimi, bayrak çelişkisi, sayfalama, drift |
| B2 | 105 kümeyi birleştir | **107 kopya silindi**, 314 fiyat taşındı, Bağcılar-2 elle |
| B3 | Görünürlüğü fiyattan türet | pg_cron JOB 5; 530 gizlendi, **200 geri geldi** |
| B4 | Moloz temizliği | 544 pasif istasyon, 729 fiyat, 9.627 geçmiş satırı |
| B5 | Madde 21–25 | Push kaldırıldı, low_priority gerçek oldu, sessiz catch'ler izli |
| B6 | Kod temizliği | 2 ölü dosya, 1 ölü fonksiyon, 12 ölü import, 4 bayat doküman bandı |
| B7 | Regresyon kilidi | +10 test (9 Python, 1 Dart) |

### Kullanıcı kararları
1. **Push altyapısı: kaldırıldı.** `push_tokens` (0 satır), `fiyat-push` Edge
   Function, `send_summary_push`, `price_alerts.push_token`. **Yerel
   bildirimler kaldı** — onlar çalışıyor.
2. **Shell'in 178 istasyonu: gizlendi** (kapasite zorlanmadı). Geri
   döndürülebilir: fiyat gelince JOB 5 bir saat içinde `visible` yapar.
3. **Moloz kapsamı daraltıldı.** Aktifteki 1.092 `unknown` satıra dokunulmadı
   (698'i meşru "bu istasyon LPG satmıyor" bilgisi).

### Plandan sapılan iki yer — ikisi de ölçüm sonucu
* **Fiyat geçmişi budaması.** Plan "90 günden eski her satırı sil" diyordu.
  Ölçüm: bu kural 1.289 istasyon-yakıt serisini tamamen silecekti ve 566'sı
  **görünür** istasyonlardaydı — 566 sparkline boşalacaktı. Kural daraltıldı:
  seri başına en yeni 20 satır daima korunur (uygulama zaten 20 gösteriyor).
* **Tamamı pasif kopya kümeleri.** 9 küme birleştirilmedi; pasif satırların
  966 fiyatının tamamı aylar önce donmuş `unknown` değerlerdi ve birleştirme
  bunlardan birini "kazanan" yapardı. Moloz temizliğine bırakıldılar.

## Kapanış doğrulaması — canlı veri

| Ölçüt | Önce | Sonra |
|---|---|---|
| Aktif kopya çifti (≤75 m) | 26 | **0** |
| Görünür ama fiyatsız istasyon | 178 | **0** |
| `aktif` + `hidden` çelişkisi | 232 | **0** (191 hidden'ın hepsi gerçekten fiyatsız) |
| `pasif` + `visible` çelişkisi | 354 | **0** |
| Pasif istasyon | 544 | **0** |
| Öksüz fiyat / geçmiş satırı | 0 | **0** |
| Açık `system_alerts` | 0 | **0** |
| `push_tokens` tablosu | var | **yok** |
| Görünür istasyon | 2.496 | **2.511** |

Marka bazında taze fiyat oranı: Petrol Ofisi %100, BP %100, Opet %99,8,
TotalEnergies %97,4, Aytemiz %97,2, Türkiye Petrolleri %89,6, Shell %79,7.
Shell dışında **bayat satır sıfır**.

Testler: **129 Python** (CI koşumu) + **27 Flutter**, hepsi yeşil.

## HÜKÜM: Faz 0, 1, 2, 3 — ✅ KAPALI

## Bilerek açık bırakılanlar (yarım iş değil, ayrı iş)

1. **A2'nin kök nedeni.** Gizleme belirtiyi çözdü, sebebi değil: Shell'in
   hedef kapsaması hâlâ eksik ve 191 istasyon fiyatsız. Gerçek çözüm hedef
   kapasitesini artırmaktır ve GitHub Actions 55 dk sınırına dayanıyor.
2. **İstasyon sayısı 2.702.** Türkiye'de ~13.000 istasyon var; kapsama ~%21.
   Bu bir *temizlik* değil *toplama* işidir (Faz 4).
3. **75–150 m bandındaki 17 çift.** Hepsi ayrı isimli gerçek istasyon
   (`YAĞLI BATI`/`YAĞLI DOĞU`, `KÜTAHYA-1`/`KÜTAHYA-2`). F3-1'in ölçülmüş
   kararına uyuldu, dokunulmadı.
4. **`_yedek_20260803_*` tabloları.** Silinen her şey geri alınabilir olsun
   diye duruyor. Bir süre sonra düşürülebilir.
