import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/station.dart';
import '../services/smart_station_service.dart';
import '../utils/distance_calculator.dart';

class StationBottomSheet extends StatelessWidget {
  final Station? visibleStation;
  final LatLng? location;
  final VoidCallback closeSheet;
  final FinancialMessage? financialMessage;
  final String selectedFuel;
  final bool isFavorite;
  final VoidCallback onFavoriteToggle;

  const StationBottomSheet({
    super.key,
    required this.visibleStation,
    required this.location,
    required this.closeSheet,
    required this.financialMessage,
    required this.selectedFuel,
    required this.isFavorite,
    required this.onFavoriteToggle,
  });

  String _getLogoPath(String marka) {
    switch (marka) {
      case 'Shell':
        return 'assets/shell.png.png';
      case 'Opet':
        return 'assets/opet.png.png';
      case 'Petrol Ofisi':
        return 'assets/po.png.png';
      case 'BP':
        return 'assets/bp.png.png';
      case 'TotalEnergies':
        return 'assets/total.png.png';
      default:
        return 'assets/icon.png';
    }
  }

  void _openDirections(double lat, double lng, String name) async {
    final uri = Uri.parse('google.navigation:q=$lat,$lng&mode=d');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else {
      final webUri = Uri.parse(
          'https://www.google.com/maps/dir/?api=1&destination=$lat,$lng');
      if (await canLaunchUrl(webUri)) {
        await launchUrl(webUri);
      }
    }
  }

  String _sourceLabel(Station station) {
    final source = station.dataSource.toLowerCase();
    if (source.contains('api.opet.com.tr')) return 'Opet resmi fiyat listesi';
    if (source.contains('akaryakit-fiyatlari-bp')) {
      return 'BP resmi fiyat listesi';
    }
    if (source.contains('petrolofisi.com.tr')) {
      return 'Petrol Ofisi resmi fiyat listesi';
    }
    if (source.contains('aytemiz.com.tr')) return 'Aytemiz resmi fiyat listesi';
    if (source.contains('guzelenerji.com.tr')) {
      return 'TotalEnergies resmi fiyat listesi';
    }
    if (source.contains('tppd.com.tr')) {
      return 'Türkiye Petrolleri resmi fiyat listesi';
    }
    if (source.contains('turkiyeshell.com')) return 'Shell resmi fiyat listesi';
    return station.dataSource.isEmpty
        ? 'Kaynak bekleniyor'
        : station.dataSource;
  }

  String _formatUpdatedAt(DateTime? dateTime) {
    if (dateTime == null) return 'Güncelleme bekleniyor';
    final local = dateTime.toLocal();
    final day = local.day.toString().padLeft(2, '0');
    final month = local.month.toString().padLeft(2, '0');
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '$day.$month.${local.year} $hour:$minute';
  }

  @override
  Widget build(BuildContext context) {
    if (visibleStation == null) return const SizedBox.shrink();

    final station = visibleStation!;
    final enlem = station.latitude;
    final boylam = station.longitude;
    final distance = (location != null && enlem != null && boylam != null)
        ? getDistanceKm(location!.latitude, location!.longitude, enlem, boylam)
        : null;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 40),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(30), topRight: Radius.circular(30)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.15),
              offset: const Offset(0, -5),
              blurRadius: 15,
            )
          ]),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (financialMessage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: financialMessage!.type == 'success'
                    ? const Color(0xFFDCFCE7)
                    : financialMessage!.type == 'danger'
                        ? const Color(0xFFFEE2E2)
                        : const Color(0xFFFEF9C3),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                financialMessage!.text,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  height: 1.4,
                  color: financialMessage!.type == 'success'
                      ? const Color(0xFF166534)
                      : financialMessage!.type == 'danger'
                          ? const Color(0xFF991B1B)
                          : const Color(0xFF854D0E),
                ),
              ),
            ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    // Note: We need to ensure assets exist. They will error if missing.
                    Container(
                      width: 48,
                      height: 48,
                      margin: const EdgeInsets.only(right: 16),
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: [
                            BoxShadow(
                                color: Colors.black.withOpacity(0.1),
                                offset: const Offset(0, 2),
                                blurRadius: 4)
                          ]),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        // Fallback icon icon if asset fails
                        child: Image.asset(
                          _getLogoPath(station.brand),
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stackTrace) =>
                              const Icon(Icons.local_gas_station,
                                  size: 30, color: Colors.grey),
                        ),
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(station.brand,
                              style: const TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w900,
                                  color: Color(0xFFFF5A5F),
                                  height: 1.1)),
                          Text(station.displayName,
                              style: const TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF666666),
                                  height: 1.5),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              const Icon(Icons.schedule_rounded,
                                  size: 13, color: Color(0xFF6B7280)),
                              const SizedBox(width: 3),
                              Text(station.getLastPriceChangeText(),
                                  style: const TextStyle(
                                      fontSize: 10,
                                      color: Color(0xFF6B7280),
                                      fontWeight: FontWeight.bold)),
                              const SizedBox(width: 10),
                              if (distance != null)
                                Flexible(
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.directions_car_rounded,
                                          size: 14, color: Color(0xFF00B84F)),
                                      const SizedBox(width: 3),
                                      Flexible(
                                        child: Text(
                                          '${distance.toStringAsFixed(1)} km uzakta',
                                          style: const TextStyle(
                                              fontSize: 12,
                                              fontWeight: FontWeight.w800,
                                              color: Color(0xFF00B84F)),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                            ],
                          )
                        ],
                      ),
                    )
                  ],
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  GestureDetector(
                    onTap: onFavoriteToggle,
                    child: Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                          color: isFavorite
                              ? const Color(0xFFFFF7ED)
                              : const Color(0xFFF3F4F6),
                          borderRadius: BorderRadius.circular(20)),
                      child: Icon(
                        isFavorite
                            ? Icons.star_rounded
                            : Icons.star_border_rounded,
                        color: isFavorite
                            ? const Color(0xFFF59E0B)
                            : const Color(0xFF666666),
                        size: 21,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: closeSheet,
                    child: Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                          color: const Color(0xFFF3F4F6),
                          borderRadius: BorderRadius.circular(20)),
                      child: const Icon(Icons.close_rounded,
                          color: Color(0xFF666666), size: 20),
                    ),
                  ),
                ],
              )
            ],
          ),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFBFDBFE)),
            ),
            child: Row(
              children: [
                const Icon(Icons.verified_rounded,
                    size: 18, color: Color(0xFF2563EB)),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _sourceLabel(station),
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF1E3A8A),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Bölgesel resmi fiyat - ${_formatUpdatedAt(station.latestPriceUpdatedAt)}',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF3B5F9A),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: const Color(0xFFF9FAFB),
                borderRadius: BorderRadius.circular(16)),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildPriceBox('Benzin', 'Kursunsuz 95'),
                _buildPriceBox('Motorin', 'Motorin'),
                _buildPriceBox('LPG', 'LPG'),
              ],
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                if (enlem != null && boylam != null) {
                  _openDirections(enlem, boylam, station.displayName);
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF00B84F),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16)),
                elevation: 5,
                shadowColor: const Color(0xFF00B84F).withOpacity(0.5),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.near_me_rounded, color: Colors.white, size: 20),
                  SizedBox(width: 8),
                  Text('Yol Tarifi Al',
                      style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                          letterSpacing: 0.5)),
                ],
              ),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildPriceBox(String label, String targetType) {
    final priceRaw = visibleStation!.priceTextFor(targetType);
    final isMissing = priceRaw == '-';
    final trend = visibleStation!.trendFor(targetType);
    final isSelected = selectedFuel == targetType;

    return Expanded(
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color:
                isSelected ? const Color(0xFFD1D5DB) : const Color(0xFFE5E7EB),
            width: 1,
          ),
        ),
        child: Column(
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: isSelected
                    ? const Color(0xFF111827)
                    : const Color(0xFF9CA3AF),
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 6),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    isMissing ? 'Yok' : '$priceRaw TL',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                      color: isMissing
                          ? const Color(0xFFD1D5DB)
                          : const Color(0xFF1F2937),
                    ),
                  ),
                  if (!isMissing && trend != null)
                    Padding(
                      padding: const EdgeInsets.only(left: 4),
                      child: Icon(
                        trend < 0
                            ? Icons.arrow_downward_rounded
                            : trend > 0
                                ? Icons.arrow_upward_rounded
                                : Icons.remove_rounded,
                        color: trend < 0
                            ? const Color(0xFF16A34A)
                            : trend > 0
                                ? const Color(0xFFDC2626)
                                : const Color(0xFF6B7280),
                        size: 16,
                      ),
                    )
                ],
              ),
            )
          ],
        ),
      ),
    );
  }
}
