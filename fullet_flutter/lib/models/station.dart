import 'fuel_price.dart';
import 'price_history.dart';
import '../utils/price_formatter.dart';
import 'package:google_maps_cluster_manager_2/google_maps_cluster_manager_2.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class Station with ClusterItem {
  final String id;
  final String brand;
  final String name;
  final String city;
  final String district;
  final double? latitude;
  final double? longitude;
  final String dataSource;
  final bool isActive;
  final String visibilityStatus;
  final DateTime? dataUpdatedAt;
  final List<FuelPrice> prices;
  final List<PriceHistory> priceHistory;

  Station({
    required this.id,
    required this.brand,
    required this.name,
    required this.city,
    required this.district,
    required this.latitude,
    required this.longitude,
    required this.dataSource,
    required this.isActive,
    required this.visibilityStatus,
    required this.dataUpdatedAt,
    required this.prices,
    required this.priceHistory,
  });

  factory Station.fromJson(Map<String, dynamic> json) {
    final rawPrices = json['fiyatlar'];
    final rawHistory = json['fiyat_gecmisi'];

    final isActive = json['aktif'] == null || json['aktif'] == true;
    final visibilityStatus =
        json['visibility_status']?.toString().toLowerCase().trim() ??
            (isActive ? 'visible' : 'hidden');

    return Station(
      id: json['id']?.toString() ?? '',
      brand: json['marka']?.toString() ?? '',
      name: json['isim']?.toString() ?? '',
      city: json['il']?.toString() ?? '',
      district: json['ilce']?.toString() ?? '',
      latitude: double.tryParse(json['enlem']?.toString() ?? ''),
      longitude: double.tryParse(json['boylam']?.toString() ?? ''),
      dataSource: json['veri_kaynagi']?.toString() ?? '',
      isActive: isActive,
      visibilityStatus: visibilityStatus,
      dataUpdatedAt:
          DateTime.tryParse(json['guncellenme_tarihi']?.toString() ?? ''),
      prices: rawPrices is List
          ? rawPrices
              .whereType<Map<String, dynamic>>()
              .map((item) {
                try {
                  return FuelPrice.fromJson(item);
                } catch (_) {
                  return null;
                }
              })
              .whereType<FuelPrice>()
              .toList()
          : const [],
      priceHistory: rawHistory is List
          ? rawHistory
              .whereType<Map<String, dynamic>>()
              .map(PriceHistory.fromJson)
              .toList()
          : const [],
    );
  }

  bool get hasLocation => latitude != null && longitude != null;

  @override
  LatLng get location => LatLng(latitude ?? 0, longitude ?? 0);

  bool get isLowPriority => visibilityStatus == 'low_priority';

  bool get isVisibleInApp =>
      visibilityStatus == 'visible' || visibilityStatus == 'low_priority';

  String get displayName {
    if (name.isEmpty || name == brand) {
      return district.isEmpty ? brand : '$brand - $district';
    }
    return name;
  }

  FuelPrice? priceFor(String selectedFuel) {
    for (final price in prices) {
      if (fuelMatches(price.fuelType, selectedFuel)) {
        return price;
      }
    }
    return null;
  }

  FuelPrice? displayPriceFor(String selectedFuel) {
    final price = priceFor(selectedFuel);
    if (price == null || !price.isDisplayable) return null;
    return price;
  }

  FuelPrice? trustedPriceFor(String selectedFuel) {
    final price = priceFor(selectedFuel);
    if (price == null || !price.isTrustedForCalculations) return null;
    return price;
  }

  /// TEK BAYAT FİYAT POLİTİKASI (S2-2).
  ///
  /// Haritada gösterilen fiyat ile "en ucuz" / "en mantıklı" hesabının
  /// kullandığı fiyat AYNI havuzdan gelir: `fresh` + `stale` (yani
  /// `isDisplayable`), `unknown` hariç. Eskiden marker bayat fiyatı
  /// gösterirken taç yalnızca taze fiyatlar arasından seçiliyordu; kullanıcı
  /// ekranda 79,50 yazan bir marker görürken mavi rozet 82,10'daki başka bir
  /// istasyonda duruyordu. Bayatlık artık fiyatı havuzdan çıkararak değil,
  /// marker'ın turuncu paletiyle ve fiyat durumu bandıyla anlatılır.
  double? priceValueFor(String selectedFuel) =>
      displayPriceFor(selectedFuel)?.price;

  /// Yalnızca `fresh`. Haritada/sıralamada KULLANILMAZ — bkz. [priceValueFor].
  /// Yalnızca kullanıcıya bildirim gönderen fiyat alarmı gibi, yanlış tetiklenmesi
  /// gösterimden daha maliyetli olan yüzeyler için ayrılmıştır.
  double? trustedPriceValueFor(String selectedFuel) =>
      trustedPriceFor(selectedFuel)?.price;

  String priceStatusFor(String selectedFuel) =>
      priceFor(selectedFuel)?.priceStatus ?? 'unknown';

  bool hasFreshPriceFor(String selectedFuel) =>
      priceFor(selectedFuel)?.isFresh ?? false;

  bool hasDisplayablePriceFor(String selectedFuel) =>
      displayPriceFor(selectedFuel) != null;

  String priceTextFor(String selectedFuel) {
    return displayPriceFor(selectedFuel)?.formatted ?? '-';
  }

  PriceHistory? latestHistoryFor(String selectedFuel) {
    final matches = priceHistory
        .where((item) => fuelMatches(item.fuelType, selectedFuel))
        .where((item) => item.changedAt != null)
        .toList()
      ..sort((a, b) => b.changedAt!.compareTo(a.changedAt!));
    return matches.isEmpty ? null : matches.first;
  }

  double? trendFor(String selectedFuel) =>
      latestHistoryFor(selectedFuel)?.difference;

  /// Yalnızca FİYAT satırlarının zaman damgası (S2-3).
  ///
  /// Eskiden listeye `dataUpdatedAt` (= `istasyonlar.guncellenme_tarihi`) de
  /// giriyordu. O kolon `matching._station_targets` tarafından her bot
  /// koşusunda, hiç fiyat yazılmasa bile güncelleniyor; sonuç olarak üç
  /// haftalık bir fiyat "Güncel" görünebiliyordu. İstasyon satırının
  /// güncellenme zamanı fiyat tazeliği değildir.
  DateTime? get latestPriceUpdatedAt {
    final candidates =
        prices.map((price) => price.updatedAt).whereType<DateTime>().toList();
    if (candidates.isEmpty) return null;
    candidates.sort((a, b) => b.compareTo(a));
    return candidates.first;
  }

  bool get hasOfficialRegionalSource {
    final source = dataSource.toLowerCase();
    return source.contains('opet.com.tr') ||
        source.contains('petrolofisi.com.tr') ||
        source.contains('aytemiz.com.tr') ||
        source.contains('guzelenerji.com.tr') ||
        source.contains('tppd.com.tr') ||
        source.contains('turkiyeshell.com');
  }

  bool get hasOfficialStationSource {
    final source = dataSource.toLowerCase();
    return source.contains('find.shell.com/tr/fuel') ||
        source.contains('apimobile.guzelenerji.com.tr/exapi/stations') ||
        source.contains('tppd.com.tr/tr/stationmaplist');
  }

  /// Seçili yakıtın son fiyat değişimini anlatır (S2-3).
  ///
  /// Eskiden `priceHistory` yakıt tipine BAKILMADAN taranıyordu; motorin
  /// değişimi LPG kartında "3s önce" olarak gösterilebiliyordu. Artık geçmiş
  /// de, geri düşüş de seçili yakıtın kendi satırından okunur.
  String getLastPriceChangeText(String selectedFuel) {
    final latestChange = latestHistoryFor(selectedFuel)?.changedAt;
    if (latestChange != null) return _relativeTime(latestChange);

    final latestUpdate = priceFor(selectedFuel)?.updatedAt;
    if (latestUpdate == null) return 'Yeni';
    return _relativeTime(latestUpdate);
  }

  String _relativeTime(DateTime dateTime) {
    final diffHours = DateTime.now().difference(dateTime).inHours;
    if (diffHours <= 0) return 'Güncel';
    if (diffHours < 24) return '${diffHours}s önce';
    return '${diffHours ~/ 24} gün önce';
  }
}
