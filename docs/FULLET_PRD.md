# FULLET — PRODUCT REQUIREMENTS DOCUMENT
### Sprint 1 · Sprint 2 · Sprint 3 | Tam Uygulama Planı

> **Versiyon:** 1.1.0 → 1.3.0 | **Hedef Platform:** Android (Flutter)  
> **Geliştirici:** Tek kişi | **Başlangıç Tarihi:** Haziran 2026

---

# SPRINT 1 — TEMEL İYİLEŞTİRMELER
**Hedef:** Mevcut eksiklikler düzeltilir, analytics kurulur, onboarding eklenir.  
**Süre:** ~10-12 gün  
**Versiyon Hedefi:** 1.1.0

---

## S1-F1: Firebase Analytics Entegrasyonu

### Problem
Uygulamanın hangi özelliklerinin kullanıldığı, kullanıcının nerede bıraktığı, Garajım doluluk oranı, Akıllı Mod kullanımı — hiçbiri bilinmiyor. Tüm geliştirme kararları kördür.

### Amaç
Temel kullanım metriklerini ve dönüşüm hunisini izlemek. Hangi özelliğin gerçekten değer ürettiğini veriyle kanıtlamak.

### Kullanıcı Hikayesi
Bu özellik kullanıcıya doğrudan görünmez. Geliştirici için.

### Başarı Metrikleri
- Analytics dashboard 7 gün içinde anlamlı veri üretiyor
- Garajım doluluk oranı ilk kez ölçülebilir hale geldi
- Station tapped → directions_requested dönüşüm oranı izlenebilir

### Teknik Gereksinimler

**pubspec.yaml'a eklenecek paket:**
```yaml
firebase_analytics: ^10.10.0
```
> Not: `firebase_core` ve `firebase_crashlytics` zaten mevcut. `google-services.json` zaten entegre.

**Yeni dosya: `lib/services/analytics_service.dart`**
```dart
import 'package:firebase_analytics/firebase_analytics.dart';

class AnalyticsService {
  static final FirebaseAnalytics _analytics = FirebaseAnalytics.instance;

  // Uygulama olayları
  static Future<void> logAppOpen() async =>
      _analytics.logAppOpen();

  static Future<void> logStationTapped({
    required String stationId,
    required String brand,
    required String selectedFuel,
    required double? price,
  }) async =>
      _analytics.logEvent(name: 'station_tapped', parameters: {
        'station_id': stationId,
        'brand': brand,
        'fuel_type': selectedFuel,
        'price': price ?? 0.0,
      });

  static Future<void> logFuelTypeChanged(String fuelType) async =>
      _analytics.logEvent(name: 'fuel_type_changed', parameters: {
        'fuel_type': fuelType,
      });

  static Future<void> logDirectionsRequested({
    required String stationId,
    required String brand,
  }) async =>
      _analytics.logEvent(name: 'directions_requested', parameters: {
        'station_id': stationId,
        'brand': brand,
      });

  static Future<void> logGarageOpened() async =>
      _analytics.logEvent(name: 'garage_opened');

  static Future<void> logGarageVehicleSet({
    required String make,
    required String model,
  }) async =>
      _analytics.logEvent(name: 'garage_vehicle_set', parameters: {
        'make': make,
        'model': model,
      });

  static Future<void> logGarageVehicleCleared() async =>
      _analytics.logEvent(name: 'garage_vehicle_cleared');

  static Future<void> logSearchPerformed(String query) async =>
      _analytics.logEvent(name: 'search_performed', parameters: {
        'query': query,
      });

  static Future<void> logFavoriteToggled({
    required String stationId,
    required bool isFavorited,
  }) async =>
      _analytics.logEvent(name: 'favorite_toggled', parameters: {
        'station_id': stationId,
        'is_favorited': isFavorited,
      });

  static Future<void> logBrandFilterChanged(List<String> brands) async =>
      _analytics.logEvent(name: 'brand_filter_changed', parameters: {
        'brands': brands.join(','),
        'count': brands.length,
      });

  static Future<void> logFocusModeChanged(String mode) async =>
      _analytics.logEvent(name: 'focus_mode_changed', parameters: {
        'mode': mode,
      });

  static Future<void> logOnboardingCompleted() async =>
      _analytics.logEvent(name: 'onboarding_completed');

  static Future<void> logOnboardingSkipped(int step) async =>
      _analytics.logEvent(name: 'onboarding_skipped', parameters: {
        'at_step': step,
      });

  static Future<void> logSmartSelectionSeen({
    required String messageType, // success, warning, danger
  }) async =>
      _analytics.logEvent(name: 'smart_selection_seen', parameters: {
        'message_type': messageType,
      });
}
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `pubspec.yaml` | `firebase_analytics` paketi eklenir |
| `lib/services/analytics_service.dart` | **[YENİ]** Yukarıdaki servis oluşturulur |
| `lib/screens/modern_map_screen.dart` | `_selectStation`, `_onFuelChipTapped`, `_openDirectionsToStation` içine event çağrıları eklenir |
| `lib/widgets/garage_modal.dart` | `updateCarSelection` ve `clearVehicle` çağrılarına event eklenir |
| `lib/widgets/station_bottom_sheet.dart` | "Yol Tarifi Al" butonuna ve favori toggle'a event eklenir |

### Entegrasyon Noktaları (Modern Map Screen)

`modern_map_screen.dart` içinde aşağıdaki yerlere çağrı eklenir:

```dart
// _selectStation metoduna:
AnalyticsService.logStationTapped(
  stationId: station.id,
  brand: station.brand,
  selectedFuel: prefs.selectedFuel,
  price: station.priceValueFor(prefs.selectedFuel),
);

// _buildFuelChipBar içinde GestureDetector.onTap'e:
AnalyticsService.logFuelTypeChanged(fuelKey);

// GarageBottomSheet açılınca:
AnalyticsService.logGarageOpened();
```

### Analytics Eventleri (Tam Liste)

| Event | Tetikleyici | Parametreler |
|-------|-------------|-------------|
| `app_open` | Uygulama açılışı | — |
| `station_tapped` | Marker'a tıklama | station_id, brand, fuel_type, price |
| `fuel_type_changed` | Chip bar değişimi | fuel_type |
| `directions_requested` | "Yol Tarifi Al" butonu | station_id, brand |
| `garage_opened` | Garajım açılması | — |
| `garage_vehicle_set` | Araç seçilmesi | make, model |
| `garage_vehicle_cleared` | Araç kaldırılması | — |
| `search_performed` | Arama yapılması | query |
| `favorite_toggled` | Favori ekleme/çıkarma | station_id, is_favorited |
| `brand_filter_changed` | Marka filtresi değişimi | brands, count |
| `focus_mode_changed` | Focus mod değişimi | mode |
| `onboarding_completed` | Onboarding tamamlanması | — |
| `onboarding_skipped` | Onboarding atlanması | at_step |
| `smart_selection_seen` | Smart mesaj görünmesi | message_type |

### Edge Case'ler
- Firebase başlatılmamışsa `logEvent` çağrıları crash etmemeli → `try/catch` ile sarılır
- Offline durumda eventler Firebase SDK tarafından yerel olarak kuyruklanır, bağlantıda otomatik gönderilir (SDK bunu handle eder)

### Kabul Kriterleri
- [ ] Firebase Analytics dashboard'unda 24 saat içinde event'ler görünüyor
- [ ] `station_tapped` eventi station ID ile doğru kaydediliyor
- [ ] Uygulama release modunda da crash yapmıyor (Crashlytics kontrolü)
- [ ] `firebase_analytics` debug view ile tüm event'ler test edildi

### Riskler
- Firebase `google-services.json` içindeki paket adı `com.fullet.app` ile uyuşmalı
- Analytics SDK boyutu APK'ya ~500KB ekler — göz ardı edilebilir

---

## S1-F2: Onboarding (İlk Açılış Akışı)

### Problem
Kullanıcı uygulamayı açınca doğrudan haritaya düşüyor. Uygulamanın ne yaptığı, Akıllı Mod nedir, neden araç eklemeli — hiçbiri anlatılmıyor. D1 retention düşük.

### Amaç
İlk açılışta uygulamanın değer önerisini 3 adımda anlatmak ve kullanıcıyı Garajım'a yönlendirmek.

### Kullanıcı Hikayesi
> "Uygulamayı ilk indiren biri olarak, uygulamanın ne işe yaradığını anlamak istiyorum. Aracımı ekleyerek daha iyi fiyat önerileri alabildiğimi bilmek istiyorum."

### Başarı Metrikleri
- Onboarding completion rate > %60
- Garajım doluluğu ilk 24 saatte ölçülebilir artış (analytics ile)
- D1 retention %15+ artış (baseline analytics kurulunca ölçülecek)

### UI Değişiklikleri

**Yeni dosya: `lib/screens/onboarding_screen.dart`**

3 kartlık tam ekran onboarding. Tasarım prensipleri:
- Arka plan: FulColors.primary gradient (#00D4AA → #0099CC)
- Her kart: Emoji/ikon + başlık + açıklama + ilerleme göstergesi
- "Atla" butonu: Sağ üst köşe, her adımda görünür
- "Sonraki" / "Hadi Başla" (son adım): Alt CTA butonu

**Kart 1 — Değer Önerisi:**
```
🗺️
Yakınındaki Tüm Fiyatlar
Türkiye'deki akaryakıt istasyonlarının
güncel fiyatları, tek haritada.
```

**Kart 2 — Akıllı Mod:**
```
🧠
Sana Özel Akıllı Seçim
Aracını ekle. Biz de sana sadece
ucuz değil, en mantıklı istasyonu bulalım.
```

**Kart 3 — Resmi Kaynak:**
```
✅
Resmi Kaynaklardan, Güvenilir Fiyat
Shell, Opet, Petrol Ofisi ve diğerlerinin
resmi fiyat listelerinden anlık veri.
```

**Son adım butonu:**
```
Aracımı Ekle → [Garajım açılır]
```

Altında:
```
Şimdi değil, haritaya geç →
```

### UX Akışı

```
İlk kurulum
    ↓
SharedPreferences'ta 'onboarding_done' key yoksa
    ↓
OnboardingScreen gösterilir (full screen)
    ↓
[Kart 1] → [Kart 2] → [Kart 3]
    ↓
"Aracımı Ekle" → GarageBottomSheet açılır
    ↓ (Garajım kapatılınca)
ModernMapScreen'e geçilir
    ↓
SharedPreferences'a 'onboarding_done: true' yazılır

--- VEYA ---

"Şimdi değil" → ModernMapScreen'e geçilir
SharedPreferences'a 'onboarding_done: true' yazılır
AnalyticsService.logOnboardingSkipped(stepIndex) çağrılır
```

### Teknik Gereksinimler

**`lib/main.dart` değişikliği:**
```dart
// Mevcut: direkt ModernMapScreen
// Yeni: onboarding kontrolü

Future<Widget> _getInitialScreen() async {
  final prefs = await SharedPreferences.getInstance();
  final done = prefs.getBool('onboarding_done') ?? false;
  if (done) return const ModernMapScreen();
  return const OnboardingScreen();
}

// MaterialApp.home içinde:
home: FutureBuilder<Widget>(
  future: _getInitialScreen(),
  builder: (ctx, snap) {
    if (!snap.hasData) return const SplashScreen(); // veya loading
    return snap.data!;
  },
),
```

**`lib/screens/onboarding_screen.dart` — Yeni dosya:**
```dart
class OnboardingScreen extends StatefulWidget { ... }

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _currentPage = 0;

  final List<_OnboardingPage> pages = [
    _OnboardingPage(
      emoji: '🗺️',
      title: 'Yakınındaki Tüm Fiyatlar',
      description: 'Türkiye\'deki akaryakıt istasyonlarının güncel fiyatları, tek haritada.',
    ),
    _OnboardingPage(
      emoji: '🧠',
      title: 'Sana Özel Akıllı Seçim',
      description: 'Aracını ekle. Biz de sana sadece ucuz değil, en mantıklı istasyonu bulalım.',
    ),
    _OnboardingPage(
      emoji: '✅',
      title: 'Resmi Kaynaklardan Güvenilir Fiyat',
      description: 'Shell, Opet, Petrol Ofisi ve diğerlerinin resmi verilerinden anlık bilgi.',
    ),
  ];

  void _complete({bool withGarage = false}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_done', true);
    AnalyticsService.logOnboardingCompleted();
    if (!mounted) return;
    if (withGarage) {
      // ModernMapScreen'e git ve Garajım aç
      Navigator.pushReplacement(context, MaterialPageRoute(
        builder: (_) => const ModernMapScreen(openGarageOnStart: true),
      ));
    } else {
      Navigator.pushReplacement(context, MaterialPageRoute(
        builder: (_) => const ModernMapScreen(),
      ));
    }
  }
  // ...
}
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/screens/onboarding_screen.dart` | **[YENİ]** Oluşturulur |
| `lib/main.dart` | `_getInitialScreen()` fonksiyonu + FutureBuilder |
| `lib/screens/modern_map_screen.dart` | `openGarageOnStart` opsiyonel parametresi eklenir |

### Edge Case'ler
- Onboarding gösterilirken uygulama arka plana giderse state korunur (PageController)
- İnternet yok durumunda onboarding hala çalışır (lokal içerik)
- Kullanıcı onboarding'de "Aracımı Ekle"ye basıp Garajım'ı doldurmadan kapatırsa → haritaya normal açılır, `onboarding_done: true` yazılır

### Kabul Kriterleri
- [ ] Uygulama ilk kurulumda OnboardingScreen gösteriyor
- [ ] İkinci açılışta OnboardingScreen gösterilmiyor
- [ ] "Atla" butonu her sayfada çalışıyor
- [ ] "Aracımı Ekle" → GarageBottomSheet açılıyor
- [ ] GarageBottomSheet kapanınca harita açılıyor
- [ ] `onboarding_completed` veya `onboarding_skipped` eventi Firebase'e gidiyor
- [ ] Animasyonlar flutter_animate ile fade+slide — jank yok

### Riskler
- `ModernMapScreen`'e `openGarageOnStart` parametresi eklemek mevcut code flow'u bozmamalı → `false` default değeri ile güvenli
- FutureBuilder boş state'te splash göstermeli, blank screen olmamalı

---

## S1-F3: Garajım Aktivasyon Bağlantısı

### Problem
Garajım doldurulmamışken Akıllı Mod, default 50L/7L değerleriyle hesap yapıyor. Kullanıcı bu hesabın aracına göre olmadığını bilmiyor. Garajım boş kullanıcılarda Smart Selection anlamsız.

### Amaç
Garajım boşken StationBottomSheet'te bağlamsal prompt göster. Kullanıcı garajını doldurunca "hesap güncellendi" feedback ver.

### Kullanıcı Hikayesi
> "Bir istasyona tıkladığımda 'En Mantıklı Seçim' yazısını görüyorum ama neden o istasyon seçildi anlamıyorum. Kendi aracıma göre hesap yapılmasını istiyorum."

### Başarı Metrikleri
- Garage fill rate analytics'te +20% (7 gün baseline sonrası)
- `garage_opened` event'i StationBottomSheet üzerinden tetiklenme oranı ölçülebilir

### UI Değişiklikleri

**`station_bottom_sheet.dart` içinde, FinancialMessage kartının altına:**

```dart
// Garajım boşsa bağlamsal prompt
if (!prefs.hasVehicle) ...[
  const SizedBox(height: 8),
  GestureDetector(
    onTap: () {
      Navigator.pop(context); // sheet kapat
      GarageBottomSheet.show(context, isDark: isDark);
    },
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: FulColors.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: FulColors.primary.withOpacity(0.3)),
      ),
      child: Row(children: [
        const Icon(Icons.directions_car_rounded, 
          color: FulColors.primary, size: 16),
        const SizedBox(width: 8),
        Expanded(child: Text(
          'Aracını ekle, sana özel hesaplama yap',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: FulColors.primary,
          ),
        )),
        const Icon(Icons.chevron_right_rounded,
          color: FulColors.primary, size: 16),
      ]),
    ),
  ),
],
```

**`UserPreferencesProvider`'a getter ekle:**
```dart
bool get hasVehicle => selectedMake != null && selectedModel != null;
```

**`StationBottomSheet` parametrelerine ekle:**
```dart
required bool hasVehicle,
required VoidCallback onGaragePromptTap,
```

### UX Akışı

```
Kullanıcı markere tıklar
    ↓
StationBottomSheet açılır
    ↓
[Garajım DOLU] → mevcut Financial Message gösterilir
[Garajım BOŞ] → Financial Message + "Aracını ekle" prompt banner
    ↓
Kullanıcı "Aracını ekle"ye basar
    ↓
Bottom sheet kapanır
    ↓
GarageBottomSheet açılır
    ↓
Araç seçilir
    ↓
GarageBottomSheet kapanır
    ↓
Haritaya döner (İstasyon seçiminin devam ettirilmesi mevcut session'da olur)
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/providers/user_preferences_provider.dart` | `hasVehicle` getter eklenir |
| `lib/widgets/station_bottom_sheet.dart` | `hasVehicle` + `onGaragePromptTap` parametreleri + prompt UI |
| `lib/screens/modern_map_screen.dart` | StationBottomSheet çağrısına yeni parametreler geçilir |

### Kabul Kriterleri
- [ ] Garajım boşken istasyon sheet'inde prompt görünüyor
- [ ] Garajım doluyken prompt görünmüyor
- [ ] Prompt'a basmak sheet'i kapatıp Garajım'ı açıyor
- [ ] `garage_opened` analytics eventi tetikleniyor

---

## S1-F4: Marka Filtresi UI

### Problem
`_selectedBrands` state ve `_filteredStations()` metodu zaten var (`modern_map_screen.dart`, satır 53 ve 276). Ancak bu state'i değiştiren hiçbir UI elemanı haritada veya menüde yok. Özellik kullanılamıyor.

### Amaç
Fuel chip bar'ın altına, harita üzerinde marka filtresi chip'leri eklemek.

### Kullanıcı Hikayesi
> "Haritada sadece Shell istasyonlarını görmek istiyorum. Şu an tüm markalar çıkıyor ve istediğimi bulmak zor."

### Başarı Metrikleri
- `brand_filter_changed` eventi aktif olarak tetikleniyor
- Kullanıcıların %20+'si filtre özelliğini 30 gün içinde en az bir kez kullanıyor

### UI Değişiklikleri

Fuel chip bar'ın hemen altına scrollable marka chip row eklenir.

```
[Tüm Markalar] [Shell] [Opet] [Petrol Ofisi] [BP] [TotalEnergies] [TP] [Aytemiz]
```

Tasarım:
- `SingleChildScrollView` ile horizontal scroll
- Seçili chip: `FulColors.primary` arka plan, beyaz yazı
- Seçilmemiş: şeffaf arka plan, border
- "Tüm Markalar" chip'i `_selectedBrands.isEmpty` iken active
- Bir markaya basınca o marka toggle edilir (multi-select desteklenir)

**Widget yapısı:**
```dart
Widget _buildBrandFilterBar() {
  final allBrands = ['Shell', 'Opet', 'Petrol Ofisi', 'BP',
    'TotalEnergies', 'TP', 'Aytemiz'];
  
  return SizedBox(
    height: 34,
    child: ListView.separated(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: allBrands.length + 1, // +1 for "Tümü"
      separatorBuilder: (_, __) => const SizedBox(width: 6),
      itemBuilder: (_, i) {
        if (i == 0) return _BrandChip(
          label: 'Tümü',
          isSelected: _selectedBrands.isEmpty,
          onTap: _clearBrandFilters,
          isDark: _currentIsDark,
        );
        final brand = allBrands[i - 1];
        final isSelected = _selectedBrands.contains(brand);
        return _BrandChip(
          label: brand,
          isSelected: isSelected,
          onTap: () => _toggleBrandFilter(brand),
          isDark: _currentIsDark,
        );
      },
    ),
  );
}

void _toggleBrandFilter(String brand) {
  setState(() {
    final next = {..._selectedBrands};
    if (next.contains(brand)) {
      next.remove(brand);
    } else {
      next.add(brand);
    }
    _selectedBrands = next;
    _visibleStation = null; // Açık sheet varsa kapat
  });
  _updateCalculationsAndMarkers(forceMarkerRefresh: true);
  AnalyticsService.logBrandFilterChanged(_selectedBrands.toList());
}
```

**`modern_map_screen.dart` build metodunda konumu:**
Mevcut fuel chip bar'ın altına, harita widget'ının üstündeki Stack içindeki Column'a eklenir.

### Mevcut Kod ile Entegrasyon

`_clearBrandFilters()` metodu zaten var (satır 1161). `_selectedBrands` state zaten var (satır 53). `_filteredStations()` zaten `_selectedBrands`'ı kullanıyor (satır 276-283).

Sadece yapılacak:
1. `_buildBrandFilterBar()` widget metodu ekle
2. `_toggleBrandFilter(String brand)` metodu ekle
3. Build stack'ine `_buildBrandFilterBar()` ekle (chip bar altında)

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/screens/modern_map_screen.dart` | `_buildBrandFilterBar()` + `_toggleBrandFilter()` eklenir, build stack güncellenir |

### Edge Case'ler
- Seçili markada o bölgede istasyon yoksa → `_buildEmptyState()` zaten mevcut, `hasBrandFilter` kontrolü var
- Marka ismi değişirse database'den gelen brand string ile eşleşmeyebilir → `station.brand` exact match yapılıyor, tutarlı olmalı
- Çok fazla marka varsa chip bar yatay scroll ile yönetilir

### Kabul Kriterleri
- [ ] Chip bar fuel chip bar'ın altında görünüyor
- [ ] "Tümü" chip'i başlangıçta seçili
- [ ] Bir markaya basınca sadece o markanın istasyonları haritada görünüyor
- [ ] İkinci bir markaya basınca iki marka birden görünüyor (multi-select)
- [ ] "Tümü"ne basınca filtre temizleniyor
- [ ] Filtre aktifken boş harita state'i doğru çalışıyor
- [ ] `brand_filter_changed` eventi Firebase'e gidiyor

### Riskler
- Brand string'leri (örn: "Türkiye Petrolleri" vs "TP") Supabase'den farklı gelebilir → station.dart'ta `brand` alanı normalize edilmeli ya da marka chip label'ları DB'den gelen değerlerle eşleşmeli

---

## S1-F5: Marker Legend Overlay

### Problem
Haritada turuncu, yeşil ve mavi renkte marker'lar var. Kullanıcı bu renklerin ne anlama geldiğini bilmiyor. "En Mantıklı Seçim" ve "En Ucuz" ayrımı görsel olarak yapılmış ama legend yok.

### Amaç
Harita üzerinde küçük, sabit bir legend overlay eklemek.

### Kullanıcı Hikayesi
> "Haritada farklı renkte fiyat etiketleri görüyorum. Yeşil olanın neden farklı olduğunu bilmek istiyorum."

### Başarı Metrikleri
- Kullanıcı memnuniyet (Play Store yorumlarında "anlaşılır" ifadeleri)
- Özellik tamamen pasif, kullanım metrikleri ölçülmez

### UI Değişiklikleri

**Konum:** Harita üzerinde, sol alt köşe, FAB'ların üstü.

```dart
Widget _buildMarkerLegend() {
  final isDark = _currentIsDark;
  final bg = isDark
    ? FulColors.darkSurface.withOpacity(0.92)
    : Colors.white.withOpacity(0.92);
  
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
    decoration: BoxDecoration(
      color: bg,
      borderRadius: BorderRadius.circular(12),
      boxShadow: [BoxShadow(
        color: Colors.black.withOpacity(0.12),
        blurRadius: 8, offset: const Offset(0, 3),
      )],
    ),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _LegendItem(color: FulColors.logical, label: 'En Mantıklı'),
        const SizedBox(height: 4),
        _LegendItem(color: FulColors.info, label: 'En Ucuz'),
        const SizedBox(height: 4),
        _LegendItem(color: FulColors.primary, label: 'Diğer'),
      ],
    ),
  );
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10, height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label, style: TextStyle(
          fontFamily: 'Outfit',
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: color,
        )),
      ],
    );
  }
}
```

**Konumlandırma — `modern_map_screen.dart` build Stack'i içinde:**
```dart
Positioned(
  left: 12,
  bottom: _visibleStation != null ? bottomSheetHeight + 12 : 100,
  child: _buildMarkerLegend(),
),
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/screens/modern_map_screen.dart` | `_buildMarkerLegend()` + `_LegendItem` widget eklenir, Stack'e Positioned olarak konumlanır |

### Edge Case'ler
- Bottom sheet açıkken legend marker üstüne taşmamalı → `bottom` değeri dinamik ayarlanır
- Dark mode uyumu var (bg rengi koşullu)

### Kabul Kriterleri
- [ ] Legend harita üzerinde görünüyor
- [ ] Dark modda okunabilir
- [ ] Bottom sheet açıkken legend yukarı kayıyor veya gizleniyor
- [ ] Focus mode değişince renkler tutarlı (mevcut FulColors kullanımı)

---

## S1 Küçük Bug Fix'leri (Yarım Gün)

Ayrı PR veya tek commit:

| Fix | Dosya | Değişiklik |
|-----|-------|-----------|
| "4g önce" → "4 gün önce" | `lib/models/station.dart` | `_relativeTime()` satır 195: `'${diffHours ~/ 24}g önce'` → `'${diffHours ~/ 24} gün önce'` |
| "© 2025" → "© 2026" | Side menu veya about sayfası | Yıl güncellenir |
| "0.7 km uz..." overflow | `lib/widgets/station_bottom_sheet.dart` | Distance text'i `overflow: TextOverflow.visible` veya tam format |
| Side menu kapanma fix | `lib/widgets/ful_side_menu.dart` | Focus mode değişince `onClose()` çağrılır |
| Focus mode top bar göstergesi | `lib/widgets/top_search_bar.dart` | Focus mode badge eklenir |

---

## Sprint 1 Sonu Skor Tahmini

| Kategori | Sprint Öncesi | Sprint 1 Sonu |
|----------|--------------|---------------|
| UX | 52 | **62** |
| UI | 63 | **68** |
| Ürün Stratejisi | 28 | **42** |
| Büyüme | 35 | **45** |
| Monetizasyon | 5 | **5** |
| **Genel** | **55** | **~60** |

---
---

# SPRINT 2 — AKILLI ÖZELLİKLER
**Hedef:** Fullet'in differentiator'larını görünür kılmak. Kullanıcı uygulamanın değerini hisseder.  
**Süre:** ~10-12 gün  
**Versiyon Hedefi:** 1.2.0

---

## S2-F1: Smart Score Sistemi

### Problem
"En Mantıklı Seçim" metni var ama ne demek olduğu, nasıl hesaplandığı kullanıcıya hiç açıklanmıyor. "6.6 TL daha fazla masraf olur" rakamı nereden geliyor? Kullanıcı bu rakama güvenmiyor veya anlamıyor.

### Amaç
Her istasyona 0-100 arası bir "Akıllı Skor" vermek ve bu skoru bottom sheet'te açık, anlaşılır şekilde göstermek.

### Kullanıcı Hikayesi
> "İstasyona tıkladığımda 'neden bu istasyon daha iyi?' sorusunun cevabını görmek istiyorum. Rakamlar nereden geliyor, anlayabileyim."

### Başarı Metrikleri
- `smart_selection_seen` event'i Session başına ortalama 2+ kez tetikleniyor
- Garajım fill rate (araç ekleme → Smart Score'u anlama teşviki)

### Teknik Tasarım — Smart Score Algoritması

Mevcut `SmartStationService` sınıfına `calculateSmartScore()` metodu eklenir:

```dart
// lib/services/smart_station_service.dart'a eklenir

class SmartScore {
  final double score;           // 0-100
  final double savingsTL;       // Pozitif = kazanç, negatif = kayıp
  final double distanceKm;
  final double pricePerLiter;
  final String category;        // 'best', 'good', 'ok', 'poor'
  
  const SmartScore({
    required this.score,
    required this.savingsTL,
    required this.distanceKm,
    required this.pricePerLiter,
    required this.category,
  });
}

// SmartStationService içinde:
static SmartScore? calculateSmartScore({
  required Station station,
  required LatLng location,
  required String selectedFuel,
  required double tankCapacity,
  required double fuelConsumption,
  required SmartStationResult bestResult,
}) {
  final price = station.trustedPriceValueFor(selectedFuel);
  if (price == null) return null;

  final distanceKm = getDistanceKm(
    location.latitude, location.longitude,
    station.latitude!, station.longitude!,
  );
  if (distanceKm == null) return null;

  final myTotalCost = (tankCapacity * price) +
    (distanceKm * (fuelConsumption / 100) * price);
  final savingsTL = bestResult.bestTotalCost - myTotalCost;
  // savingsTL pozitif = bu istasyon best'ten daha iyi (normalden beklenmeyen durum)
  // savingsTL negatif = best'ten bu kadar daha pahalı

  // Score hesabı: 100 = best istasyon, 0 = en kötü
  // Max loss kabul değeri: 50 TL
  const maxLoss = 50.0;
  final normalizedLoss = (-savingsTL).clamp(0.0, maxLoss);
  final score = ((maxLoss - normalizedLoss) / maxLoss * 100).clamp(0.0, 100.0);

  String category;
  if (score >= 85) category = 'best';
  else if (score >= 65) category = 'good';
  else if (score >= 40) category = 'ok';
  else category = 'poor';

  return SmartScore(
    score: score,
    savingsTL: savingsTL,
    distanceKm: distanceKm,
    pricePerLiter: price,
    category: category,
  );
}
```

### UI Değişiklikleri

**`station_bottom_sheet.dart`'ta Smart Score kartı:**

```dart
// SmartScore gösterimi — Financial Message'ın yerine geçer veya altına eklenir
Widget _buildSmartScoreCard(SmartScore score, bool isDark) {
  final color = score.category == 'best' ? FulColors.logical
    : score.category == 'good' ? FulColors.primary
    : score.category == 'ok' ? FulColors.priceStale
    : Colors.red.shade400;
  
  final label = score.category == 'best' ? '🏆 En İyi Seçim'
    : score.category == 'good' ? '👍 İyi Seçim'
    : score.category == 'ok' ? '⚠️ Orta Seçim'
    : '⬇️ Daha İyisi Var';

  return Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: color.withOpacity(0.08),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: color.withOpacity(0.3)),
    ),
    child: Row(children: [
      // Daire progress göstergesi
      SizedBox(
        width: 52, height: 52,
        child: CircularProgressIndicator(
          value: score.score / 100,
          strokeWidth: 5,
          backgroundColor: color.withOpacity(0.2),
          valueColor: AlwaysStoppedAnimation(color),
        ),
      ),
      // Skor rakamı ortada: Stack ile
      // ...
      const SizedBox(width: 14),
      Expanded(child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(
            fontFamily: 'Outfit', fontSize: 14,
            fontWeight: FontWeight.w800, color: color,
          )),
          const SizedBox(height: 4),
          if (score.savingsTL < -1)
            Text(
              'Best seçime göre ${(-score.savingsTL).toStringAsFixed(1)} TL fazla',
              style: TextStyle(fontFamily: 'Outfit', fontSize: 12,
                fontWeight: FontWeight.w600, color: color.withOpacity(0.8)),
            )
          else
            Text(
              '${score.distanceKm.toStringAsFixed(1)} km uzakta • ${score.pricePerLiter.toStringAsFixed(2)} TL/lt',
              style: TextStyle(fontFamily: 'Outfit', fontSize: 12,
                fontWeight: FontWeight.w600, color: color.withOpacity(0.8)),
            ),
        ],
      )),
    ]),
  );
}
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/services/smart_station_service.dart` | `SmartScore` class + `calculateSmartScore()` metodu eklenir |
| `lib/widgets/station_bottom_sheet.dart` | `smartScore` parametresi + `_buildSmartScoreCard()` widget eklenir |
| `lib/screens/modern_map_screen.dart` | `_selectStation` içinde `calculateSmartScore()` çağrılır, StationBottomSheet'e geçilir |

### Edge Case'ler
- Garajım boş → `tankCapacity: 50, fuelConsumption: 7` default değerleri kullanılıyor (mevcut durum, değişmez) + "Aracını ekle" prompt gösterilir (S1-F3)
- `SmartResult` hesaplanamadıysa (istasyon sayısı < 2) → Score gösterilmez, normal Financial Message gösterilir
- Score = 100: "Bu bölgedeki tek istasyon" durumu — label "En Yakın İstasyon" olur

### Kabul Kriterleri
- [ ] Her istasyon bottom sheet'inde 0-100 arası Smart Score görünüyor
- [ ] Score rengi kategoriye göre değişiyor (yeşil/mavi/sarı/kırmızı)
- [ ] Garajım boşken score gösterilip "Aracını ekle" promptu da görünüyor
- [ ] Score hesabı SmartStationResult ile tutarlı

---

## S2-F2: Tasarruf Göstergesi

### Problem
Kullanıcı "En Mantıklı Seçim" istasyonuna gidiyor ama kaç TL tasarruf ettiğini hiç göremiyor. Tasarruf rakamı hem motivation hem retention için çok güçlü.

### Amaç
Bottom sheet'e "Bugün doldurarsan tahmini X TL ödersin" bilgisini eklemek. Session bazlı toplam tasarrufu göstermek.

### Kullanıcı Hikayesi
> "Bu istasyona gidersem ne kadar kazanacağımı ya da kaybedeceğimi somut olarak görmek istiyorum. Sadece yüzde değil, TL olarak."

### Başarı Metrikleri
- `directions_requested` event oranı artışı (tasarruf görünce navigasyon istemi artar)

### UI Değişiklikleri

**Bottom sheet'te fiyat kartlarının altına "Dolurum Toplam" bilgisi:**

```dart
// station_bottom_sheet.dart içinde fiyat bölümünün altına

Widget _buildFillCostCard({
  required double price,
  required double tankCapacity,
  required double distanceKm,
  required double fuelConsumption,
  required bool isDark,
}) {
  final fillCost = tankCapacity * price;
  final travelCost = distanceKm * (fuelConsumption / 100) * price;
  final totalCost = fillCost + travelCost;

  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    decoration: BoxDecoration(
      color: isDark ? FulColors.darkCard : FulColors.lightCard,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(
        color: isDark ? FulColors.darkBorder : FulColors.lightBorder,
      ),
    ),
    child: Row(
      children: [
        Icon(Icons.calculate_rounded, 
          color: FulColors.primary, size: 18),
        const SizedBox(width: 10),
        Expanded(child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Depo Doldurma Tahmini',
              style: TextStyle(fontFamily: 'Outfit', fontSize: 11,
                fontWeight: FontWeight.w600, 
                color: isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted)),
            const SizedBox(height: 2),
            Text(
              '${tankCapacity.toInt()} L × ${price.toStringAsFixed(2)} TL = ${fillCost.toStringAsFixed(0)} TL',
              style: TextStyle(fontFamily: 'Outfit', fontSize: 13,
                fontWeight: FontWeight.w800,
                color: isDark ? FulColors.darkText : FulColors.lightText),
            ),
            if (distanceKm > 0.3) ...[
              const SizedBox(height: 2),
              Text(
                '+ ${travelCost.toStringAsFixed(1)} TL yol masrafı → Toplam ${totalCost.toStringAsFixed(0)} TL',
                style: TextStyle(fontFamily: 'Outfit', fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted),
              ),
            ],
          ],
        )),
      ],
    ),
  );
}
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/widgets/station_bottom_sheet.dart` | `tankCapacity` + `fuelConsumption` parametreleri eklenir, `_buildFillCostCard()` eklenir |
| `lib/screens/modern_map_screen.dart` | StationBottomSheet çağrısına `prefs.tankCapacity` ve `prefs.fuelConsumption` geçilir |

### Edge Case'ler
- Garajım default değerleri (50L/7L) kullanıyorsa gösterim yine de çalışır ama kesin değil — "Kendi aracın için ayarla" küçük notu eklenebilir
- `distanceKm == null` → yol masrafı satırı gösterilmez
- Çok küçük mesafe (< 0.3km) → yol masrafı ihmal edilir, hesapta yer almaz

### Kabul Kriterleri
- [ ] Bottom sheet'te "Depo Doldurma Tahmini" kartı görünüyor
- [ ] Fiyat, depo kapasitesi ile doğru çarpılıyor
- [ ] Yol masrafı ayrıca gösteriliyor
- [ ] Dark mode'da okunabilir

---

## S2-F3: Fiyat Trend Grafiği

### Problem
`PriceHistory` modeli mevcut (`lib/models/price_history.dart`). `fiyat_gecmisi` tablosu Supabase'den çekiliyor (`supabase_service.dart`, satır 30). `Station.priceHistory` alanı doluyor. Ancak bu veri hiçbir yerde görselleştirilmiyor. Kullanıcı fiyatın yükselip yüklenmediğini bilemiyor.

### Amaç
Station bottom sheet'te seçili yakıt için son değişimleri gösteren mini trend grafiği eklemek.

### Kullanıcı Hikayesi
> "Bu istasyonun fiyatı son günlerde artıyor mu azalıyor mu? Bunu görebilsem doldurup doldurmayacağıma daha iyi karar veririm."

### Başarı Metrikleri
- Oturum uzunluğu artışı (trend grafiği kullanıcıyı daha uzun tutuyor)
- `station_tapped` sonrası session'da `directions_requested` oranı (trend gördükten sonra karar verme hızı)

### Teknik Tasarım

**Yeni paket eklenecek:**
```yaml
fl_chart: ^0.68.0
```

> Alternatif: `fl_chart` kullanmak yerine custom `CustomPainter` ile daha hafif sparkline. `fl_chart` ~2MB eklediği için custom çizim tercih edilebilir. Tercih geliştiriciye bırakılmıştır.

**Custom Sparkline (fl_chart olmadan):**

```dart
// lib/widgets/price_trend_sparkline.dart — YENİ DOSYA

import 'package:flutter/material.dart';
import '../models/price_history.dart';

class PriceTrendSparkline extends StatelessWidget {
  final List<PriceHistory> history;
  final String selectedFuel;
  final double currentPrice;
  final bool isDark;

  const PriceTrendSparkline({
    super.key,
    required this.history,
    required this.selectedFuel,
    required this.currentPrice,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    // Seçili yakıt için geçmişi filtrele ve tarihe göre sırala
    final relevant = history
        .where((h) => fuelMatches(h.fuelType, selectedFuel) && h.changedAt != null)
        .toList()
      ..sort((a, b) => a.changedAt!.compareTo(b.changedAt!));

    if (relevant.isEmpty) return const SizedBox.shrink();

    // Son 5 değişimi al
    final recent = relevant.take(5).toList();
    
    // Fiyat listesi oluştur (difference'lardan geriye hesapla)
    double runningPrice = currentPrice;
    final prices = <double>[currentPrice];
    for (final h in recent.reversed) {
      if (h.difference != null) {
        runningPrice -= h.difference!;
        prices.insert(0, runningPrice);
      }
    }

    final isRising = prices.last > prices.first;
    final trendColor = isRising ? Colors.red.shade400 : FulColors.logical;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Text('Son değişimler', style: TextStyle(
            fontFamily: 'Outfit', fontSize: 11, fontWeight: FontWeight.w600,
            color: isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted,
          )),
          const SizedBox(width: 6),
          Icon(
            isRising ? Icons.trending_up_rounded : Icons.trending_down_rounded,
            size: 14, color: trendColor,
          ),
          const SizedBox(width: 3),
          Text(
            isRising ? 'Yükseliyor' : 'Düşüyor',
            style: TextStyle(
              fontFamily: 'Outfit', fontSize: 11,
              fontWeight: FontWeight.w700, color: trendColor,
            ),
          ),
        ]),
        const SizedBox(height: 8),
        SizedBox(
          height: 40,
          child: CustomPaint(
            painter: _SparklinePainter(prices: prices, color: trendColor),
            size: const Size(double.infinity, 40),
          ),
        ),
        // Değişim listesi
        const SizedBox(height: 8),
        ...recent.map((h) => _buildHistoryRow(h, isDark)),
      ],
    );
  }

  Widget _buildHistoryRow(PriceHistory h, bool isDark) {
    final diff = h.difference;
    if (diff == null) return const SizedBox.shrink();
    final isUp = diff > 0;
    final diffColor = isUp ? Colors.red.shade400 : FulColors.logical;
    final sign = isUp ? '+' : '';
    final date = h.changedAt;
    final dateStr = date == null ? '' : _relativeDate(date);
    
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(children: [
        Icon(
          isUp ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
          size: 12, color: diffColor,
        ),
        const SizedBox(width: 4),
        Text('$sign${diff.toStringAsFixed(2)} TL',
          style: TextStyle(fontFamily: 'Outfit', fontSize: 12,
            fontWeight: FontWeight.w700, color: diffColor)),
        const Spacer(),
        Text(dateStr, style: TextStyle(fontFamily: 'Outfit', fontSize: 11,
          color: isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted)),
      ]),
    );
  }

  String _relativeDate(DateTime date) {
    final diff = DateTime.now().difference(date);
    if (diff.inHours < 24) return '${diff.inHours} saat önce';
    return '${diff.inDays} gün önce';
  }
}

class _SparklinePainter extends CustomPainter {
  final List<double> prices;
  final Color color;
  
  _SparklinePainter({required this.prices, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    if (prices.length < 2) return;
    
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    
    final min = prices.reduce((a, b) => a < b ? a : b);
    final max = prices.reduce((a, b) => a > b ? a : b);
    final range = max - min == 0 ? 1.0 : max - min;
    
    final path = Path();
    for (int i = 0; i < prices.length; i++) {
      final x = i / (prices.length - 1) * size.width;
      final y = size.height - ((prices[i] - min) / range * size.height);
      if (i == 0) path.moveTo(x, y);
      else path.lineTo(x, y);
    }
    
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(_SparklinePainter old) =>
    old.prices != prices || old.color != color;
}
```

**`station_bottom_sheet.dart`'a entegrasyon:**

PriceHistory verisi `Station` modeline zaten yükleniyor. Bottom sheet'te fiyat tablosunun altına `PriceTrendSparkline` widget'ı eklenir.

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/widgets/price_trend_sparkline.dart` | **[YENİ]** Custom painter sparkline widget |
| `lib/widgets/station_bottom_sheet.dart` | `PriceTrendSparkline` widget'ı import edilir ve eklenir |
| `pubspec.yaml` | `fl_chart` eklenir (tercih kullanılırsa) |
| `lib/utils/price_formatter.dart` | `fuelMatches()` fonksiyonunun erişilebilir olduğu kontrol edilir |

### Veri Durumu Kontrolü

`Station.priceHistory` alanı mevcut. `supabase_service.dart` satır 30'da `fiyat_gecmisi` çekiliyor. Ancak `_stationListSelect` (satır 33) içinde `fiyat_gecmisi` YOK. Sadece `_stationSelect` (satır 17) içinde var.

**Bu önemli:** Tek istasyon detayı için `fetchStations` çağrısı `_stationSelect` kullanıyor, bu yüzden `priceHistory` dolu geliyor. Eğer istasyon list view'dan seçilirse priceHistory boş olabilir.

**Çözüm:** `StationBottomSheet` priceHistory'nin boş olduğu durumu handle etmeli (`PriceTrendSparkline` null/empty check yapıyor zaten).

### Edge Case'ler
- `priceHistory` boş → Sparkline widget `const SizedBox.shrink()` döner
- Sadece 1 veri noktası → Sparkline çizilmez, değişim listesi gösterilmez
- Çok eski geçmiş (30+ gün) → "X gün önce" metni doğru çalışır
- Fiyat düştükten sonra tekrar yükseldi → Sparkline her iki yönü doğru göstermeli

### Kabul Kriterleri
- [ ] `priceHistory` olan istasyonlarda sparkline görünüyor
- [ ] Fiyat artışı kırmızı, düşüş yeşil
- [ ] "Yükseliyor / Düşüyor" etiketi ve ikon doğru
- [ ] Her değişim için "X saat önce / X gün önce" formatı
- [ ] `priceHistory` boşken widget hiç yer kaplamıyor

---

## Sprint 2 Sonu Skor Tahmini

| Kategori | Sprint 1 Sonu | Sprint 2 Sonu |
|----------|--------------|---------------|
| UX | 62 | **68** |
| UI | 68 | **73** |
| Ürün Stratejisi | 42 | **54** |
| Büyüme | 45 | **50** |
| Monetizasyon | 5 | **5** |
| **Genel** | **60** | **~65** |

---
---

# SPRINT 3 — PLATFORM ALTYAPISI
**Hedef:** Retention mekanizmaları kurulur. Kullanıcı hesabı atılır. Platform olma yolunda ilk adım.  
**Süre:** ~14-18 gün  
**Versiyon Hedefi:** 1.3.0

---

## S3-F1: Lokal Bildirimler

### Problem
Kullanıcıyı geri getiren hiçbir dışsal tetikleyici yok. Yakıt alma döngüsü 5-7 gündür. Kullanıcı uygulamayı unut; sonra aklına gelince başka kaynak kullanır.

### Amaç
Hesap gerektirmeden, lokal zamanlamaya dayalı hatırlatıcı bildirimler kurmak.

### Kullanıcı Hikayesi
> "Yakıt almam gerektiğinde uygulamayı açmayı unutuyorum. Uygun bir zamanda hatırlatılmak istiyorum."

### Başarı Metrikleri
- D7 retention +8-10 puan (analytics baseline ile ölçülür)
- Bildirimden gelen session oranı Firebase'de ölçülür (UTM eşdeğeri analytics event)

### Teknik Gereksinimler

**Yeni paket:**
```yaml
flutter_local_notifications: ^17.2.2
```

**Yeni dosya: `lib/services/notification_service.dart`**

```dart
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz;

class NotificationService {
  static final FlutterLocalNotificationsPlugin _plugin =
    FlutterLocalNotificationsPlugin();
  
  static Future<void> initialize() async {
    tz.initializeTimeZones();
    
    const AndroidInitializationSettings android =
      AndroidInitializationSettings('@mipmap/ic_launcher');
    
    await _plugin.initialize(
      const InitializationSettings(android: android),
      onDidReceiveNotificationResponse: _onNotificationTap,
    );
  }

  static void _onNotificationTap(NotificationResponse response) {
    // App açılıyor, analytics event log et
    AnalyticsService.logEvent('notification_opened', {
      'notification_id': response.id ?? 0,
      'payload': response.payload ?? '',
    });
  }

  static Future<bool> requestPermission() async {
    final android = _plugin.resolvePlatformSpecificImplementation<
      AndroidFlutterLocalNotificationsPlugin>();
    final granted = await android?.requestNotificationsPermission();
    return granted ?? false;
  }

  /// Periyodik yakıt hatırlatıcı — 5 gün sonra, Türkiye sabah 09:30
  static Future<void> scheduleFuelReminder() async {
    await _plugin.cancel(NotificationIds.fuelReminder);

    final now = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(
      tz.local, now.year, now.month, now.day + 5, 9, 30,
    );

    await _plugin.zonedSchedule(
      NotificationIds.fuelReminder,
      'Yakıt zamanı mı? ⛽',
      'Yakınındaki güncel fiyatları kontrol et',
      scheduled,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'fuel_reminder',
          'Yakıt Hatırlatıcı',
          channelDescription: 'Periyodik yakıt fiyatı hatırlatmaları',
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
          icon: '@mipmap/ic_launcher',
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
        UILocalNotificationDateInterpretation.absoluteTime,
      payload: 'fuel_reminder',
    );
  }

  /// Onboarding tamamlanmadan 24 saat sonra hatırlatıcı
  static Future<void> scheduleGarageReminder() async {
    await _plugin.cancel(NotificationIds.garageReminder);

    final scheduled = tz.TZDateTime.now(tz.local).add(const Duration(hours: 24));
    
    await _plugin.zonedSchedule(
      NotificationIds.garageReminder,
      'Aracını henüz eklemen 🚗',
      'Garajını doldur, sana özel akıllı hesap başlasın',
      scheduled,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'garage_reminder',
          'Garaj Hatırlatıcı',
          channelDescription: 'Garaj kurulum hatırlatmaları',
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
        UILocalNotificationDateInterpretation.absoluteTime,
      payload: 'garage_reminder',
    );
  }

  static Future<void> cancelGarageReminder() async =>
    _plugin.cancel(NotificationIds.garageReminder);
}

class NotificationIds {
  static const int fuelReminder = 1;
  static const int garageReminder = 2;
}
```

### UX Akışı

```
Onboarding tamamlanınca:
  → scheduleFuelReminder() — 5 gün sonra
  → scheduleGarageReminder() — 24 saat sonra (Garajım boşsa)

Garajım doldurulunca:
  → cancelGarageReminder() — garage hatırlatıcı iptal

Bildirime tıklanınca:
  → Uygulama açılır
  → AnalyticsService.logEvent('notification_opened') çağrılır
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `pubspec.yaml` | `flutter_local_notifications`, `timezone` eklenir |
| `lib/services/notification_service.dart` | **[YENİ]** |
| `lib/main.dart` | `NotificationService.initialize()` çağrılır |
| `lib/screens/onboarding_screen.dart` | Tamamlanınca `scheduleReminders()` çağrılır |
| `lib/providers/user_preferences_provider.dart` | `updateCarSelection` içinde `cancelGarageReminder()` çağrılır |
| `android/app/src/main/AndroidManifest.xml` | `SCHEDULE_EXACT_ALARM` veya `USE_EXACT_ALARM` izni eklenir |

### AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
<uses-permission android:name="android.permission.VIBRATE"/>
<!-- API 33+ için bildirim izni -->
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
```

### Edge Case'ler
- Kullanıcı bildirim iznini reddederse → `scheduleFuelReminder` çağrısı sessizce fail eder, uygulama çalışmaya devam eder
- Telefon yeniden başlatılırsa → `flutter_local_notifications` boot receiver ile bildirimleri yeniden planlar
- Kullanıcı bildirimleri sistem ayarlarından kapatırsa → izin kontrolü her açılışta yapılabilir ama zorunlu değil

### Kabul Kriterleri
- [ ] Onboarding sonrası 5 gün sonrası için bildirim planlanıyor
- [ ] Garajım boşsa 24 saat sonra hatırlatıcı planlanıyor
- [ ] Garajım doldurulunca hatırlatıcı iptal ediliyor
- [ ] Android 13+ için izin akışı çalışıyor
- [ ] Bildirime tıklanınca uygulama açılıyor

---

## S3-F2: Favori İstasyon İyileştirmeleri

### Problem
Favori ekleme özelliği var ama favorilerin görüntülendiği bir liste yok. Kullanıcı eklediği favorilere nasıl ulaşacağını bilmiyor. Search ekranında badge var ama erişim flow'u belirsiz.

### Amaç
Side menu veya dedicated ekrana "Favorilerim" listesi eklemek. Favori istasyonlar haritada öne çıkarılmalı.

### Kullanıcı Hikayesi
> "Sık gittiğim istasyonları favorilere ekledim. Onları hızlıca listeleyip fiyatlarını görmek istiyorum."

### Başarı Metrikleri
- `favorite_toggled` event oranı artışı
- Favori listesine erişim sayısı (yeni analytics event)

### UI Değişiklikleri

**Yeni tab/bölüm: Side menu'ya "Favorilerim" bölümü eklenir.**

`ful_side_menu.dart` içindeki mevcut bölüm yapısına ek olarak:

```dart
// Favoriler bölümü
if (prefs.favoriteStationIds.isNotEmpty) ...[
  const SizedBox(height: 16),
  Text('Favorilerim',
    style: TextStyle(fontFamily: 'Outfit', fontSize: 13,
      fontWeight: FontWeight.w800, color: mutedColor)),
  const SizedBox(height: 8),
  ...prefs.favoriteStationIds.take(5).map((stationId) =>
    FavoriteStationTile(
      stationId: stationId,
      allStations: allStations, // Mevcut station listesinden bulunur
      selectedFuel: prefs.selectedFuel,
      onTap: (station) {
        onClose();
        onStationSelected(station);
      },
    )
  ),
  if (prefs.favoriteStationIds.length > 5)
    TextButton(
      onPressed: () => _showAllFavorites(context),
      child: Text('Tümünü gör (${prefs.favoriteStationIds.length})',
        style: const TextStyle(fontFamily: 'Outfit', fontSize: 12)),
    ),
],
```

**`FavoriteStationTile` widget:**

```dart
class FavoriteStationTile extends StatelessWidget {
  final String stationId;
  final List<Station> allStations;
  final String selectedFuel;
  final void Function(Station) onTap;
  
  @override
  Widget build(BuildContext context) {
    final station = allStations.firstWhere(
      (s) => s.id == stationId,
      orElse: () => null, // handle not found
    );
    
    if (station == null) return const SizedBox.shrink();
    
    final price = station.priceTextFor(selectedFuel);
    final trend = station.trendFor(selectedFuel);
    
    return GestureDetector(
      onTap: () => onTap(station),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        margin: const EdgeInsets.only(bottom: 6),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border),
        ),
        child: Row(children: [
          // Brand logo küçük
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: Image.asset(_logoPath(station.brand), width: 28, height: 28),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(station.displayName, style: TextStyle(
                fontFamily: 'Outfit', fontSize: 13,
                fontWeight: FontWeight.w700, color: textColor,
              )),
              Text(station.district, style: TextStyle(
                fontFamily: 'Outfit', fontSize: 11, color: mutedColor)),
            ],
          )),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(price, style: const TextStyle(
                fontFamily: 'Outfit', fontSize: 14,
                fontWeight: FontWeight.w800, color: FulColors.primary,
              )),
              if (trend != null)
                Icon(
                  trend > 0 ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
                  size: 12,
                  color: trend > 0 ? Colors.red.shade400 : FulColors.logical,
                ),
            ],
          ),
        ]),
      ),
    );
  }
}
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `lib/widgets/ful_side_menu.dart` | "Favorilerim" bölümü eklenir |
| `lib/widgets/favorite_station_tile.dart` | **[YENİ]** |

### Kabul Kriterleri
- [ ] Side menu'da favoriler listesi görünüyor
- [ ] Favori yoksa bölüm görünmüyor
- [ ] Favori istasyona tıklanınca haritada o istasyon seçiliyor
- [ ] Fiyat ve trend bilgisi gösteriliyor
- [ ] Favori ekleme/çıkarma hala çalışıyor

---

## S3-F3: Kullanıcı Hesabı

### Problem
Favoriler, araç, geçmiş — hepsi cihazda `SharedPreferences` ile saklanıyor. Cihaz değişince sıfırlanıyor. Push notification, monetizasyon, cross-device sync mümkün değil.

### Amaç
Anonim kullanıcı kimliği oluşturup verilerini Supabase'de saklamak. Google Sign-In ile opsiyonel yükseltme.

### Kullanıcı Hikayesi
> "Telefon aldım ve uygulamayı yeniden kurdum. Favori istasyonlarım ve araç bilgim hala olsun istiyorum."

### Başarı Metrikleri
- Kullanıcı kayıt oranı (anonim → Google upgrade)
- Cross-device retention (D30 retained user oranı)

### Teknik Tasarım

**Yaklaşım: Progressive Authentication**
1. Uygulama ilk açılışta anonim Firebase Auth kullanıcısı oluşturur (otomatik, görünmez)
2. Veriler Supabase'e `user_id` ile yazılır (favoriler, araç, tercihler)
3. Kullanıcı "Hesabımı Kaydet"e basınca Google Sign-In'e yönlendirilir
4. Anonim hesap Google hesabı ile merge edilir, veri kaybolmaz

**Yeni paketler:**
```yaml
firebase_auth: ^4.17.0
google_sign_in: ^6.2.1
```

**Yeni dosya: `lib/services/auth_service.dart`**

```dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AuthService {
  static final FirebaseAuth _auth = FirebaseAuth.instance;
  static final GoogleSignIn _google = GoogleSignIn();

  static User? get currentUser => _auth.currentUser;
  static String? get userId => _auth.currentUser?.uid;
  static bool get isAnonymous => _auth.currentUser?.isAnonymous ?? true;

  /// Uygulama açılışında çağrılır
  static Future<void> initializeUser() async {
    if (_auth.currentUser == null) {
      await _auth.signInAnonymously();
    }
  }

  /// Google ile yükseltme
  static Future<bool> upgradeWithGoogle() async {
    try {
      final googleUser = await _google.signIn();
      if (googleUser == null) return false;
      
      final googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );
      
      // Anonim hesabı Google ile merge et
      await _auth.currentUser!.linkWithCredential(credential);
      return true;
    } on FirebaseAuthException catch (e) {
      if (e.code == 'credential-already-in-use') {
        // Bu Google hesabı başka bir Fullet hesabıyla bağlı
        // → merge gerekebilir, şimdilik sign-in yap
        await _auth.signInWithCredential(e.credential!);
        return true;
      }
      return false;
    }
  }

  static Future<void> signOut() async {
    await _google.signOut();
    await _auth.signOut();
    await _auth.signInAnonymously(); // Anonim devam
  }
}
```

**Supabase'de yeni tablo (migration):**
```sql
-- user_profiles tablosu
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firebase_uid TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- user_favorites tablosu
CREATE TABLE user_favorites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firebase_uid TEXT NOT NULL REFERENCES user_profiles(firebase_uid),
  station_id TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(firebase_uid, station_id)
);

-- user_preferences tablosu  
CREATE TABLE user_preferences (
  firebase_uid TEXT PRIMARY KEY REFERENCES user_profiles(firebase_uid),
  selected_fuel TEXT DEFAULT 'Kursunsuz 95',
  tank_capacity FLOAT DEFAULT 50.0,
  fuel_consumption FLOAT DEFAULT 7.0,
  selected_make TEXT,
  selected_model TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policies
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Kullanıcı sadece kendi datasına erişir
-- (Firebase JWT ile RLS — Supabase'de Firebase Auth entegrasyonu gerekir)
```

**`UserPreferencesProvider` güncellenir:**

```dart
// Mevcut SharedPreferences yazmaları Supabase'e de senkronize edilir
// Double-write pattern: önce SharedPreferences (hızlı UI), sonra Supabase (kalıcı)

Future<void> updateTankCapacity(double val) async {
  tankCapacity = val;
  notifyListeners();
  // Lokal
  final prefs = await SharedPreferences.getInstance();
  await prefs.setDouble('tankCapacity', val);
  // Cloud
  await _syncToCloud();
}

Future<void> _syncToCloud() async {
  final uid = AuthService.userId;
  if (uid == null) return;
  await SupabaseService.upsertUserPreferences(uid, this);
}
```

### Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `pubspec.yaml` | `firebase_auth`, `google_sign_in` eklenir |
| `lib/services/auth_service.dart` | **[YENİ]** |
| `lib/services/supabase_service.dart` | `upsertUserPreferences`, `syncFavorites` metodları eklenir |
| `lib/providers/user_preferences_provider.dart` | Cloud sync metodları eklenir |
| `lib/main.dart` | `AuthService.initializeUser()` çağrılır |
| `lib/widgets/ful_side_menu.dart` | "Hesabımı Kaydet" butonu eklenir |
| `android/app/google-services.json` | Firebase Auth için proje güncellenir |
| `android/app/src/main/AndroidManifest.xml` | Google Sign-In için intent-filter |

### Veri Migrasyon Stratejisi

```
İlk açılış (mevcut kullanıcı):
  → SharedPreferences'ta veri var
  → Anonim Firebase kullanıcı oluştur
  → SharedPreferences'tan Supabase'e tek seferlik sync
  → 'cloud_synced' flag SharedPreferences'a yazılır

İkinci açılış:
  → 'cloud_synced' flag var → normal çalışma
  → Double-write: lokal + cloud
```

### Edge Case'ler
- Google Sign-In başarısız → anonim devam, veri kaybolmaz
- İnternet yokken favoriler değişirse → SharedPreferences'ta tutar, sonraki bağlantıda sync
- `credential-already-in-use` → mevcut Google hesabına sign-in, veri merge edilir
- Supabase RLS Firebase Auth JWT'yi doğrulamalı → Supabase Firebase Auth entegrasyon dökümantasyonu takip edilmeli

### Kabul Kriterleri
- [ ] Uygulama açılışında anonim kullanıcı oluşturuluyor
- [ ] Favori ekleme Supabase'e yazılıyor
- [ ] Google Sign-In çalışıyor
- [ ] Google Sign-In sonrası anonim favoriler korunuyor
- [ ] Telefon değişince favoriler Google hesabıyla geri geliyor
- [ ] Çevrimdışı çalışmaya devam ediyor

---

## Sprint 3 Sonu Skor Tahmini

| Kategori | Sprint 2 Sonu | Sprint 3 Sonu |
|----------|--------------|---------------|
| UX | 68 | **72** |
| UI | 73 | **74** |
| Ürün Stratejisi | 54 | **62** |
| Büyüme | 50 | **63** |
| Monetizasyon | 5 | **18** |
| **Genel** | **65** | **~72** |

---
---

# ÖZET: TÜM SPRİNTLER

## Dosya Değişim Özeti

| Dosya | Sprint 1 | Sprint 2 | Sprint 3 |
|-------|----------|----------|----------|
| `pubspec.yaml` | analytics | fl_chart | firebase_auth, google_sign_in, local_notifications |
| `lib/main.dart` | onboarding check | — | auth init, notification init |
| `lib/screens/modern_map_screen.dart` | brand filter, legend, garage prompt param | smart score call | — |
| `lib/screens/onboarding_screen.dart` | **[YENİ]** | — | notification schedule |
| `lib/services/analytics_service.dart` | **[YENİ]** | logSmartScore | logNotificationOpened |
| `lib/services/auth_service.dart` | — | — | **[YENİ]** |
| `lib/services/notification_service.dart` | — | — | **[YENİ]** |
| `lib/services/smart_station_service.dart` | — | SmartScore class | — |
| `lib/services/supabase_service.dart` | — | — | upsertPreferences |
| `lib/providers/user_preferences_provider.dart` | hasVehicle getter | — | cloud sync |
| `lib/widgets/station_bottom_sheet.dart` | garage prompt | smart score, fill cost, sparkline | — |
| `lib/widgets/ful_side_menu.dart` | — | — | favorites list |
| `lib/widgets/price_trend_sparkline.dart` | — | **[YENİ]** | — |
| `lib/widgets/favorite_station_tile.dart` | — | — | **[YENİ]** |
| `lib/models/station.dart` | — | — | — |

## Yeni Bağımlılıklar

| Paket | Sprint | Versiyon |
|-------|--------|---------|
| `firebase_analytics` | 1 | ^10.10.0 |
| `fl_chart` (opsiyonel) | 2 | ^0.68.0 |
| `firebase_auth` | 3 | ^4.17.0 |
| `google_sign_in` | 3 | ^6.2.1 |
| `flutter_local_notifications` | 3 | ^17.2.2 |
| `timezone` | 3 | ^0.9.4 |

## Supabase Değişiklikleri

| Sprint | Değişiklik |
|--------|-----------|
| Sprint 1 | Yok |
| Sprint 2 | Yok |
| Sprint 3 | `user_profiles`, `user_favorites`, `user_preferences` tabloları + RLS |

## Kritik Riskler

| Risk | Sprint | Etki | Önlem |
|------|--------|------|-------|
| `brand` string mismatch | 1 | Marka filtresi çalışmaz | Station.brand normalize edilmeli |
| `.env` APK içinde | 1 | Güvenlik açığı | Dart define veya obfuscation |
| `priceHistory` boş gelme | 2 | Sparkline görünmez | Empty check zorunlu |
| Firebase Auth + Supabase RLS entegrasyonu | 3 | Veri erişim hatası | Supabase JWT dokümanı takip edilmeli |
| Google Sign-In SHA-1 | 3 | Sign-In çalışmaz | Play Console SHA-1 Firebase'e eklenmeli |

---

*PRD sonu. Her özellik bu dokümana göre doğrudan geliştirmeye başlanabilir.*
