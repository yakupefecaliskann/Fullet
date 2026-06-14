import '../utils/price_formatter.dart';

class FuelPrice {
  final String fuelType;
  final double price;
  final String priceStatus;
  final DateTime? updatedAt;

  const FuelPrice({
    required this.fuelType,
    required this.price,
    this.priceStatus = 'fresh',
    this.updatedAt,
  });

  factory FuelPrice.fromJson(Map<String, dynamic> json) {
    final parsedPrice = parseFuelPrice(json['fiyat'])?.toDouble();
    if (parsedPrice == null) {
      throw const FormatException('Invalid fuel price');
    }

    return FuelPrice(
      fuelType: json['yakit_tipi']?.toString() ?? '',
      price: parsedPrice,
      priceStatus:
          json['price_status']?.toString().toLowerCase().trim() ?? 'fresh',
      updatedAt: DateTime.tryParse(json['son_guncelleme']?.toString() ?? ''),
    );
  }

  bool get isFresh => priceStatus == 'fresh';
  bool get isStale => priceStatus == 'stale';
  bool get isUnknown => priceStatus == 'unknown';
  bool get isDisplayable => !isUnknown;
  bool get isTrustedForCalculations => isFresh;

  String get formatted => price.toStringAsFixed(2);
}
