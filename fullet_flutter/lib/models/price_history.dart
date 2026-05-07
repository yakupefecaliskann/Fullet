import '../utils/price_formatter.dart';

class PriceHistory {
  final String fuelType;
  final double? difference;
  final DateTime? changedAt;

  const PriceHistory({
    required this.fuelType,
    required this.difference,
    required this.changedAt,
  });

  factory PriceHistory.fromJson(Map<String, dynamic> json) {
    return PriceHistory(
      fuelType: json['yakit_tipi']?.toString() ?? '',
      difference: parseFuelPrice(json['fiyat_farki'])?.toDouble(),
      changedAt: DateTime.tryParse(json['degisim_tarihi']?.toString() ?? ''),
    );
  }
}
