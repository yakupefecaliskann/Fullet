import '../utils/price_formatter.dart';

class FuelPrice {
  final String fuelType;
  final double price;
  final DateTime? updatedAt;

  const FuelPrice({
    required this.fuelType,
    required this.price,
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
      updatedAt: DateTime.tryParse(json['son_guncelleme']?.toString() ?? ''),
    );
  }

  String get formatted => price.toStringAsFixed(2);
}
