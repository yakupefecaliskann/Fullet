class PriceAlert {
  final String id;
  final String stationId;
  final String fuelType;
  final double thresholdPrice;
  final bool active;
  final DateTime? lastTriggeredAt;

  const PriceAlert({
    required this.id,
    required this.stationId,
    required this.fuelType,
    required this.thresholdPrice,
    required this.active,
    this.lastTriggeredAt,
  });

  factory PriceAlert.fromJson(Map<String, dynamic> json) {
    final triggered = json['son_tetiklenme'];
    return PriceAlert(
      id: json['id'] as String,
      stationId: json['istasyon_id'] as String,
      fuelType: json['yakit_tipi'] as String,
      thresholdPrice: (json['esik_fiyat'] as num).toDouble(),
      active: json['aktif'] as bool? ?? true,
      lastTriggeredAt:
          triggered == null ? null : DateTime.tryParse(triggered as String),
    );
  }
}
