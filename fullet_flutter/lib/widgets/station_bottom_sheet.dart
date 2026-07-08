import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/station.dart';
import '../services/smart_station_service.dart';
import '../utils/distance_calculator.dart';
import '../theme/ful_theme.dart';
import 'price_trend_sparkline.dart';

/// Fiyat durumu (fresh/stale/unknown) için proje genelinde tutarlı renk —
/// istasyon detayı ve fiyata göre sıralı liste aynı görsel dili kullanır.
Color priceStatusColor(String? status) {
  switch (status) {
    case 'fresh':
      return FulColors.priceFresh;
    case 'stale':
      return FulColors.priceStale;
    default:
      return FulColors.priceUnknown;
  }
}

class StationBottomSheet extends StatefulWidget {
  final Station? visibleStation;
  final LatLng? location;
  final VoidCallback closeSheet;
  final SmartScore? smartScore;
  final double tankCapacity;
  final double fuelConsumption;
  final String selectedFuel;
  final bool isFavorite;
  final VoidCallback onFavoriteToggle;
  final bool hasVehicle;
  final VoidCallback onGaragePromptTap;
  final VoidCallback onGaragePromptClose;
  final Future<void> Function(Station station) onDirectionsRequested;
  final VoidCallback? onPriceAlertTap;
  final VoidCallback? onPurchaseConfirmed;

  const StationBottomSheet({
    super.key,
    required this.visibleStation,
    required this.location,
    required this.closeSheet,
    required this.smartScore,
    required this.tankCapacity,
    required this.fuelConsumption,
    required this.selectedFuel,
    required this.isFavorite,
    required this.onFavoriteToggle,
    required this.hasVehicle,
    required this.onGaragePromptTap,
    required this.onGaragePromptClose,
    required this.onDirectionsRequested,
    required this.onPriceAlertTap,
    required this.onPurchaseConfirmed,
  });

  @override
  State<StationBottomSheet> createState() => _StationBottomSheetState();
}

class _StationBottomSheetState extends State<StationBottomSheet> {
  bool _expanded = false;

  @override
  void didUpdateWidget(StationBottomSheet old) {
    super.didUpdateWidget(old);
    // Yeni istasyon seçilince peek'e geri dön
    if (old.visibleStation?.id != widget.visibleStation?.id) {
      _expanded = false;
    }
  }

  String _logoPath(String brand) {
    switch (brand.trim()) {
      case 'Shell':
        return 'assets/logo_shell.png';
      case 'Opet':
        return 'assets/logo_opet.png';
      case 'Petrol Ofisi':
        return 'assets/logo_petrol_ofisi.png';
      case 'BP':
        return 'assets/logo_bp.png';
      case 'TotalEnergies':
        return 'assets/logo_totalenergies.png';
      case 'Türkiye Petrolleri':
      case 'Turkiye Petrolleri':
      case 'TP':
        return 'assets/logo_turkiye_petrolleri.png';
      case 'Aytemiz':
        return 'assets/logo_aytemiz.png';
      default:
        return 'assets/icon.png';
    }
  }

  Future<void> _openDirections(double lat, double lng) async {
    final uri = Uri.parse('google.navigation:q=$lat,$lng&mode=d');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
      return;
    }
    final webUri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=$lat,$lng');
    await launchUrl(webUri, mode: LaunchMode.externalApplication);
  }

  String _priceStatusLabel(String? status, DateTime? updatedAt) {
    if (status == 'stale') {
      if (updatedAt != null) {
        final hours = DateTime.now().difference(updatedAt).inHours;
        if (hours >= 48) return '⚠️ ${hours ~/ 24} gün önce güncellendi';
        return '⚠️ $hours saat önce güncellendi';
      }
      return '⚠️ Bayat fiyat';
    }
    if (status == 'unknown') return 'ℹ️ Fiyat teyit aşamasında';
    if (status == null) return 'ℹ️ Fiyat bilgisi bulunamadı';
    return '✓ Doğrulanmış fiyat';
  }

  String _sourceLabel(Station station) {
    final src = station.dataSource.toLowerCase();
    if (src.contains('opet')) return 'Opet resmi fiyat listesi';
    if (src.contains('bp')) return 'BP resmi fiyat listesi';
    if (src.contains('petrolofisi')) return 'Petrol Ofisi resmi fiyat listesi';
    if (src.contains('aytemiz')) return 'Aytemiz resmi fiyat listesi';
    if (src.contains('guzelenerji') || src.contains('total')) {
      return 'TotalEnergies resmi fiyat listesi';
    }
    if (src.contains('tppd') || src.contains('tp')) {
      return 'Türkiye Petrolleri resmi fiyat listesi';
    }
    if (src.contains('shell')) return 'Shell resmi fiyat listesi';
    return 'Fullet veri tabanı';
  }

  @override
  Widget build(BuildContext context) {
    final station = widget.visibleStation;
    if (station == null) return const SizedBox.shrink();

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surface = isDark ? FulColors.darkSurface : FulColors.lightSurface;
    final cardBg = isDark ? FulColors.darkCard : FulColors.lightCard;
    final border = isDark ? FulColors.darkBorder : FulColors.lightBorder;
    final textColor = isDark ? FulColors.darkText : FulColors.lightText;
    final mutedColor =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;
    final brandColor = brandColorFor(station.brand);

    final priceText = station.priceTextFor(widget.selectedFuel);
    final priceValue = station.priceValueFor(widget.selectedFuel);
    final hasPrice = priceValue != null;
    final lat = station.latitude;
    final lng = station.longitude;
    final distKm = (widget.location != null && lat != null && lng != null)
        ? getDistanceKm(
            widget.location!.latitude, widget.location!.longitude, lat, lng)
        : null;

    final priceStatus = station.priceStatusFor(widget.selectedFuel);
    final priceUpdatedAt =
        station.priceFor(widget.selectedFuel)?.updatedAt ?? station.dataUpdatedAt;
    final shouldShowPriceStatus =
        hasPrice || priceStatus != 'fresh' || station.isLowPriority;

    return GestureDetector(
      onTap: () {},
      onVerticalDragEnd: (details) {
        final v = details.primaryVelocity ?? 0;
        if (v < -300 && !_expanded) setState(() => _expanded = true);
        if (v > 300 && _expanded) setState(() => _expanded = false);
      },
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            decoration: BoxDecoration(
              color: surface.withOpacity(isDark ? 0.92 : 0.97),
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(28)),
              border: Border(
                top: BorderSide(color: border.withOpacity(0.6), width: 1),
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Drag handle — tap to toggle expand
                GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => setState(() => _expanded = !_expanded),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(0, 10, 0, 8),
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: isDark
                            ? FulColors.darkBorder
                            : const Color(0xFFD1D5DB),
                        borderRadius: BorderRadius.circular(999),
                      ),
                    ),
                  ),
                ),

                // Price status bant
                if (shouldShowPriceStatus)
                  _PriceStatusBand(
                    status: priceStatus,
                    label: _priceStatusLabel(priceStatus, priceUpdatedAt),
                    color: priceStatusColor(priceStatus),
                  ),

                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // ── Header: logo + isim + favori + kapat ──
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 54,
                            height: 54,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: cardBg,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: border, width: 1),
                              boxShadow: [
                                BoxShadow(
                                  color: brandColor.withOpacity(0.15),
                                  blurRadius: 10,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Image.asset(
                              _logoPath(station.brand),
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => Icon(
                                Icons.local_gas_station_rounded,
                                color: brandColor,
                                size: 28,
                              ),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  station.brand,
                                  style: TextStyle(
                                    fontFamily: 'Outfit',
                                    fontWeight: FontWeight.w900,
                                    fontSize: 18,
                                    color: textColor,
                                    height: 1.2,
                                  ),
                                ),
                                if (station.name.isNotEmpty &&
                                    station.name != station.brand)
                                  Text(
                                    station.name,
                                    style: TextStyle(
                                      fontFamily: 'Outfit',
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13,
                                      color: mutedColor,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                if (station.district.isNotEmpty ||
                                    station.city.isNotEmpty) ...[
                                  const SizedBox(height: 2),
                                  Row(
                                    children: [
                                      Icon(Icons.location_on_rounded,
                                          size: 12, color: mutedColor),
                                      const SizedBox(width: 3),
                                      Expanded(
                                        child: Text(
                                          [station.district, station.city]
                                              .where((s) => s.isNotEmpty)
                                              .join(', '),
                                          style: TextStyle(
                                            fontFamily: 'Outfit',
                                            fontSize: 11,
                                            color: mutedColor,
                                            fontWeight: FontWeight.w500,
                                          ),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ],
                            ),
                          ),
                          Column(
                            children: [
                              GestureDetector(
                                onTap: widget.onFavoriteToggle,
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 200),
                                  width: 38,
                                  height: 38,
                                  decoration: BoxDecoration(
                                    color: widget.isFavorite
                                        ? FulColors.danger.withOpacity(0.12)
                                        : cardBg,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: widget.isFavorite
                                          ? FulColors.danger.withOpacity(0.4)
                                          : border,
                                    ),
                                  ),
                                  child: Icon(
                                    widget.isFavorite
                                        ? Icons.favorite_rounded
                                        : Icons.favorite_border_rounded,
                                    color: widget.isFavorite
                                        ? FulColors.danger
                                        : mutedColor,
                                    size: 18,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 4),
                              GestureDetector(
                                onTap: widget.closeSheet,
                                child: Container(
                                  width: 38,
                                  height: 38,
                                  decoration: BoxDecoration(
                                    color: cardBg,
                                    shape: BoxShape.circle,
                                    border: Border.all(color: border),
                                  ),
                                  child: Icon(Icons.close_rounded,
                                      color: mutedColor, size: 18),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),

                      const SizedBox(height: 16),

                      // ── Fiyat + mesafe kartları — PEEK'TE DE GÖRÜNÜR ──
                      Row(
                        children: [
                          Expanded(
                            flex: 3,
                            child: _InfoCard(
                              isDark: isDark,
                              cardBg: cardBg,
                              border: border,
                              label: _fuelLabel(widget.selectedFuel),
                              value:
                                  hasPrice ? '$priceText ₺' : 'Fiyat yok',
                              valueColor: hasPrice
                                  ? priceStatusColor(priceStatus)
                                  : mutedColor,
                              icon: Icons.local_gas_station_rounded,
                              iconColor: brandColor,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            flex: 2,
                            child: _InfoCard(
                              isDark: isDark,
                              cardBg: cardBg,
                              border: border,
                              label: 'Mesafe',
                              value: distKm != null
                                  ? distKm < 1
                                      ? '${(distKm * 1000).toStringAsFixed(0)} m'
                                      : '${distKm.toStringAsFixed(1)} km'
                                  : '-',
                              valueColor: FulColors.info,
                              icon: Icons.near_me_rounded,
                              iconColor: FulColors.info,
                            ),
                          ),
                        ],
                      ),

                      // ── Navigasyon butonu — PEEK'TE DE GÖRÜNÜR ──
                      if (lat != null && lng != null) ...[
                        const SizedBox(height: 12),
                        GestureDetector(
                          onTap: () async {
                            await widget.onDirectionsRequested(station);
                            await _openDirections(lat, lng);
                          },
                          child: Container(
                            height: 52,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                colors: [
                                  FulColors.primary,
                                  FulColors.primaryDark
                                ],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              borderRadius: BorderRadius.circular(16),
                              boxShadow: [
                                BoxShadow(
                                  color: FulColors.primary.withOpacity(0.45),
                                  blurRadius: 16,
                                  offset: const Offset(0, 6),
                                ),
                              ],
                            ),
                            child: const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.navigation_rounded,
                                    color: Colors.white, size: 20),
                                SizedBox(width: 8),
                                Text(
                                  'Yol Tarifi Al',
                                  style: TextStyle(
                                    fontFamily: 'Outfit',
                                    color: Colors.white,
                                    fontWeight: FontWeight.w800,
                                    fontSize: 16,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        GestureDetector(
                          onTap: widget.onPriceAlertTap,
                          child: Container(
                            height: 44,
                            decoration: BoxDecoration(
                              color: cardBg,
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: border),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.notifications_active_outlined,
                                    color: FulColors.primary, size: 18),
                                const SizedBox(width: 8),
                                Text(
                                  'Fiyat Alarmı Kur',
                                  style: TextStyle(
                                    fontFamily: 'Outfit',
                                    color: textColor,
                                    fontWeight: FontWeight.w700,
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        if (widget.smartScore != null) ...[
                          const SizedBox(height: 8),
                          GestureDetector(
                            onTap: widget.onPurchaseConfirmed,
                            child: Container(
                              height: 44,
                              decoration: BoxDecoration(
                                color: cardBg,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: border),
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Text('⛽', style: TextStyle(fontSize: 16)),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Buradan Aldım',
                                    style: TextStyle(
                                      fontFamily: 'Outfit',
                                      color: textColor,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ],

                      // ── Genişleyen bölüm ──
                      AnimatedSize(
                        duration: const Duration(milliseconds: 320),
                        curve: Curves.easeOutCubic,
                        child: _expanded
                            ? Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  if (widget.smartScore != null) ...[
                                    const SizedBox(height: 10),
                                    _SmartScoreCard(
                                      score: widget.smartScore!,
                                      isDark: isDark,
                                      cardBg: cardBg,
                                      border: border,
                                      textColor: textColor,
                                      mutedColor: mutedColor,
                                    ),
                                  ],
                                  if (hasPrice) ...[
                                    const SizedBox(height: 10),
                                    _FillCostCard(
                                      price: priceValue,
                                      tankCapacity: widget.tankCapacity,
                                      distanceKm: distKm,
                                      fuelConsumption: widget.fuelConsumption,
                                      isDark: isDark,
                                      cardBg: cardBg,
                                      border: border,
                                      textColor: textColor,
                                      mutedColor: mutedColor,
                                    ),
                                  ],
                                  if (hasPrice) ...[
                                    const SizedBox(height: 10),
                                    PriceTrendSparkline(
                                      history: station.priceHistory,
                                      selectedFuel: widget.selectedFuel,
                                      currentPrice: priceValue,
                                      isDark: isDark,
                                    ),
                                  ],
                                  if (!widget.hasVehicle) ...[
                                    const SizedBox(height: 10),
                                    _GaragePromptCard(
                                      isDark: isDark,
                                      onClose: widget.onGaragePromptClose,
                                      onTap: widget.onGaragePromptTap,
                                    ),
                                  ],
                                  const SizedBox(height: 12),
                                  Row(
                                    children: [
                                      Icon(Icons.verified_rounded,
                                          size: 12, color: mutedColor),
                                      const SizedBox(width: 5),
                                      Expanded(
                                        child: Text(
                                          _sourceLabel(station),
                                          style: TextStyle(
                                            fontFamily: 'Outfit',
                                            fontSize: 11,
                                            color: mutedColor,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  SizedBox(
                                    height: MediaQuery.of(context).padding.bottom + 16,
                                  ),
                                ],
                              )
                            // Peek ipucu
                            : Padding(
                                padding: EdgeInsets.only(
                                  top: 10,
                                  bottom:
                                      MediaQuery.of(context).padding.bottom + 8,
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.keyboard_arrow_up_rounded,
                                        size: 16, color: mutedColor),
                                    const SizedBox(width: 4),
                                    Text(
                                      'Detaylar',
                                      style: TextStyle(
                                        fontFamily: 'Outfit',
                                        fontSize: 12,
                                        color: mutedColor,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _fuelLabel(String fuel) {
    switch (fuel) {
      case 'Kursunsuz 95':
        return 'Benzin (95)';
      case 'Motorin':
        return 'Motorin';
      case 'LPG':
        return 'LPG';
      case 'Elektrik':
        return 'Şarj';
      default:
        return fuel;
    }
  }
}

// ---------------------------------------------------------------------------
// Price Status Bant
// ---------------------------------------------------------------------------
class _PriceStatusBand extends StatelessWidget {
  final String? status;
  final String label;
  final Color color;

  const _PriceStatusBand({
    required this.status,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    if (status == 'fresh') return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 7),
      color: color.withOpacity(0.12),
      child: Row(
        children: [
          Icon(
            status == 'stale'
                ? Icons.warning_amber_rounded
                : Icons.help_outline_rounded,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Info Kartı
// ---------------------------------------------------------------------------
class _InfoCard extends StatelessWidget {
  final bool isDark;
  final Color cardBg;
  final Color border;
  final String label;
  final String value;
  final Color valueColor;
  final IconData icon;
  final Color iconColor;

  const _InfoCard({
    required this.isDark,
    required this.cardBg,
    required this.border,
    required this.label,
    required this.value,
    required this.valueColor,
    required this.icon,
    required this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 13, color: iconColor),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  label,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: isDark
                        ? FulColors.darkTextMuted
                        : FulColors.lightTextMuted,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 20,
              fontWeight: FontWeight.w900,
              color: valueColor,
              height: 1,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Smart Score Kartı
// ---------------------------------------------------------------------------
class _SmartScoreCard extends StatelessWidget {
  final SmartScore score;
  final bool isDark;
  final Color cardBg;
  final Color border;
  final Color textColor;
  final Color mutedColor;

  const _SmartScoreCard({
    required this.score,
    required this.isDark,
    required this.cardBg,
    required this.border,
    required this.textColor,
    required this.mutedColor,
  });

  @override
  Widget build(BuildContext context) {
    final color = score.category == 'best'
        ? FulColors.logical
        : score.category == 'good'
            ? FulColors.primary
            : score.category == 'ok'
                ? FulColors.priceStale
                : FulColors.danger;

    final label = score.category == 'best'
        ? '🏆 En İyi Seçim'
        : score.category == 'good'
            ? '👍 İyi Seçim'
            : score.category == 'ok'
                ? '⚠️ Orta Seçim'
                : '⬇️ Daha İyisi Var';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(isDark ? 0.12 : 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(
            width: 52,
            height: 52,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CircularProgressIndicator(
                  value: score.score / 100,
                  strokeWidth: 5,
                  backgroundColor: color.withOpacity(0.2),
                  valueColor: AlwaysStoppedAnimation(color),
                ),
                Text(
                  score.score.toInt().toString(),
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                    color: color,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                    color: textColor,
                  ),
                ),
                const SizedBox(height: 3),
                if (score.savingsTL < -1)
                  Text(
                    'En iyiye göre ${(-score.savingsTL).toStringAsFixed(1)} TL fazla masraf',
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 12,
                      color: mutedColor,
                      height: 1.3,
                    ),
                  )
                else
                  Text(
                    '${score.distanceKm.toStringAsFixed(1)} km • ${score.pricePerLiter.toStringAsFixed(2)} TL/lt',
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 12,
                      color: mutedColor,
                      height: 1.3,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Fill Cost Kartı
// ---------------------------------------------------------------------------
class _FillCostCard extends StatelessWidget {
  final double price;
  final double tankCapacity;
  final double? distanceKm;
  final double fuelConsumption;
  final bool isDark;
  final Color cardBg;
  final Color border;
  final Color textColor;
  final Color mutedColor;

  const _FillCostCard({
    required this.price,
    required this.tankCapacity,
    required this.distanceKm,
    required this.fuelConsumption,
    required this.isDark,
    required this.cardBg,
    required this.border,
    required this.textColor,
    required this.mutedColor,
  });

  @override
  Widget build(BuildContext context) {
    final fillCost = tankCapacity * price;
    final dist = distanceKm;
    final showTravel = dist != null && dist > 0.3;
    final travelCost =
        showTravel ? dist * (fuelConsumption / 100) * price : 0.0;
    final totalCost = fillCost + travelCost;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: border, width: 1),
      ),
      child: Row(
        children: [
          const Icon(Icons.calculate_rounded, color: FulColors.primary, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Depo Doldurma Tahmini',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: mutedColor,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '${tankCapacity.toInt()} L × ${price.toStringAsFixed(2)} TL = ${fillCost.toStringAsFixed(0)} TL',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: textColor,
                  ),
                ),
                if (showTravel) ...[
                  const SizedBox(height: 2),
                  Text(
                    '+ ${travelCost.toStringAsFixed(1)} TL yol → Toplam ${totalCost.toStringAsFixed(0)} TL',
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: mutedColor,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Garage Prompt Kartı
// ---------------------------------------------------------------------------
class _GaragePromptCard extends StatelessWidget {
  final bool isDark;
  final VoidCallback onClose;
  final VoidCallback onTap;

  const _GaragePromptCard({
    required this.isDark,
    required this.onClose,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        onClose();
        onTap();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          color: FulColors.primary.withOpacity(isDark ? 0.14 : 0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: FulColors.primary.withOpacity(0.34)),
        ),
        child: const Row(
          children: [
            Icon(
              Icons.directions_car_rounded,
              color: FulColors.primary,
              size: 17,
            ),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Aracını ekle, sana özel hesaplama yap',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: FulColors.primary,
                ),
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: FulColors.primary,
              size: 18,
            ),
          ],
        ),
      ),
    );
  }
}
