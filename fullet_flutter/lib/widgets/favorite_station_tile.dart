import 'package:flutter/material.dart';

import '../models/station.dart';
import '../theme/ful_theme.dart';
import '../utils/brand_utils.dart';

class FavoriteStationTile extends StatelessWidget {
  final Station station;
  final String selectedFuel;
  final VoidCallback onTap;
  final bool isDark;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const FavoriteStationTile({
    super.key,
    required this.station,
    required this.selectedFuel,
    required this.onTap,
    required this.isDark,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  Widget build(BuildContext context) {
    final price = station.priceTextFor(selectedFuel);
    final trend = station.trendFor(selectedFuel);
    final isUp = (trend ?? 0) > 0;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        margin: const EdgeInsets.only(bottom: 6),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border),
        ),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: Image.asset(
                _logoAssetFor(station.brand),
                width: 28,
                height: 28,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: FulColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Icon(
                    Icons.local_gas_station_rounded,
                    size: 16,
                    color: FulColors.primary,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    station.displayName,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: textColor,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    station.district,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 11,
                      color: mutedColor,
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  price,
                  style: const TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    color: FulColors.primary,
                  ),
                ),
                if (trend != null)
                  Icon(
                    isUp
                        ? Icons.arrow_upward_rounded
                        : Icons.arrow_downward_rounded,
                    size: 12,
                    color: isUp ? FulColors.danger : FulColors.logical,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

String _logoAssetFor(String brand) {
  switch (canonicalBrandKey(brand)) {
    case 'shell':
      return 'assets/logo_shell.png';
    case 'opet':
      return 'assets/logo_opet.png';
    case 'petrol_ofisi':
      return 'assets/logo_petrol_ofisi.png';
    case 'bp':
      return 'assets/logo_bp.png';
    case 'total':
      return 'assets/logo_totalenergies.png';
    case 'aytemiz':
      return 'assets/logo_aytemiz.png';
    case 'tp':
      return 'assets/logo_turkiye_petrolleri.png';
    default:
      return 'assets/icon.png';
  }
}
