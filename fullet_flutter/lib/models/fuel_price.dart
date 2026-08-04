import '../utils/price_formatter.dart';

class FuelPrice {
  final String fuelType;
  final double price;
  final String priceStatus;

  /// Fiyatın KAPSAMI: `regional` mi `station` mı?
  ///
  /// Ölçüldü (4 Ağustos 2026, canlı): Ankara'daki 86 Shell istasyonunun
  /// tamamı tek fiyat gösteriyor (82,08 ₺); Opet'in 22 istasyonu da öyle.
  /// Türkiye'de akaryakıt fiyatı il bazında ilan ediliyor ve markaların
  /// resmi API'leri de il bazında yayınlıyor — bugün veritabanındaki 6.718
  /// fiyat satırının %100'ü `regional`.
  ///
  /// Fiyat uydurma değil, markanın ilan ettiği gerçek fiyat. Ama bunu
  /// "bu istasyonun pompasındaki fiyat" gibi sunmak kullanıcıyı yanıltır.
  /// Bu alan, arayüzün dürüst konuşabilmesi için var.
  ///
  /// Sunucu bu alanı göndermezse `regional` varsayılır: bugünkü gerçek bu ve
  /// eksik veride "istasyondan doğrulandı" demek yanlış yönde bir hatadır.
  final String priceScope;

  final DateTime? updatedAt;

  const FuelPrice({
    required this.fuelType,
    required this.price,
    this.priceStatus = 'fresh',
    this.priceScope = 'regional',
    this.updatedAt,
  });

  factory FuelPrice.fromJson(Map<String, dynamic> json) {
    final parsedPrice = parseFuelPrice(json['fiyat'])?.toDouble();
    if (parsedPrice == null) {
      throw const FormatException('Invalid fuel price');
    }

    final rawScope =
        json['fiyat_kapsami']?.toString().toLowerCase().trim() ?? '';

    return FuelPrice(
      fuelType: json['yakit_tipi']?.toString() ?? '',
      price: parsedPrice,
      priceStatus:
          json['price_status']?.toString().toLowerCase().trim() ?? 'fresh',
      priceScope: rawScope == 'station' ? 'station' : 'regional',
      updatedAt: DateTime.tryParse(json['son_guncelleme']?.toString() ?? ''),
    );
  }

  bool get isFresh => priceStatus == 'fresh';
  bool get isStale => priceStatus == 'stale';
  bool get isUnknown => priceStatus == 'unknown';
  bool get isDisplayable => !isUnknown;
  bool get isTrustedForCalculations => isFresh;

  /// Fiyat markanın il geneli ilan fiyatı mı (istasyondan doğrulanmış değil)?
  bool get isRegionalScope => priceScope != 'station';

  /// Kullanıcıya gösterilecek kaynak açıklaması.
  /// [province] verilirse "ANKARA geneli ilan fiyatı" gibi netleşir.
  String scopeLabel({String? province}) {
    if (!isRegionalScope) return 'Bu istasyondan doğrulandı';
    final where = (province ?? '').trim();
    return where.isEmpty
        ? 'Markanın il geneli ilan fiyatı'
        : '$where geneli ilan fiyatı';
  }

  String get formatted => price.toStringAsFixed(2);
}
