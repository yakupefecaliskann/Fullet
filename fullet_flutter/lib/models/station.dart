import 'fuel_price.dart';
import 'price_history.dart';
import '../utils/price_formatter.dart';

class Station {
  final String id;
  final String brand;
  final String name;
  final String city;
  final String district;
  final double? latitude;
  final double? longitude;
  final String dataSource;
  final DateTime? dataUpdatedAt;
  final List<FuelPrice> prices;
  final List<PriceHistory> priceHistory;

  const Station({
    required this.id,
    required this.brand,
    required this.name,
    required this.city,
    required this.district,
    required this.latitude,
    required this.longitude,
    required this.dataSource,
    required this.dataUpdatedAt,
    required this.prices,
    required this.priceHistory,
  });

  factory Station.fromJson(Map<String, dynamic> json) {
    final rawPrices = json['fiyatlar'];
    final rawHistory = json['fiyat_gecmisi'];

    return Station(
      id: json['id']?.toString() ?? '',
      brand: json['marka']?.toString() ?? '',
      name: json['isim']?.toString() ?? '',
      city: json['il']?.toString() ?? '',
      district: json['ilce']?.toString() ?? '',
      latitude: double.tryParse(json['enlem']?.toString() ?? ''),
      longitude: double.tryParse(json['boylam']?.toString() ?? ''),
      dataSource: json['veri_kaynagi']?.toString() ?? '',
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

  double? priceValueFor(String selectedFuel) => priceFor(selectedFuel)?.price;

  String priceTextFor(String selectedFuel) {
    return priceFor(selectedFuel)?.formatted ?? '-';
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

  DateTime? get latestPriceUpdatedAt {
    final candidates = [
      ...prices.map((price) => price.updatedAt).whereType<DateTime>(),
      if (dataUpdatedAt != null) dataUpdatedAt!,
    ];
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

  String getLastPriceChangeText() {
    final datedHistory = priceHistory
        .where((item) => item.changedAt != null)
        .toList()
      ..sort((a, b) => b.changedAt!.compareTo(a.changedAt!));
    if (datedHistory.isEmpty) {
      final latestUpdate = latestPriceUpdatedAt;
      if (latestUpdate == null) return 'Yeni';
      return _relativeTime(latestUpdate);
    }

    return _relativeTime(datedHistory.first.changedAt!);
  }

  String _relativeTime(DateTime dateTime) {
    final diffHours = DateTime.now().difference(dateTime).inHours;
    if (diffHours <= 0) return 'Güncel';
    if (diffHours < 24) return '${diffHours}s önce';
    return '${diffHours ~/ 24}g önce';
  }
}
