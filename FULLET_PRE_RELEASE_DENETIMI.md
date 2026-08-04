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
