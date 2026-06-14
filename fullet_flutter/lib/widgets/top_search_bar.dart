import 'package:flutter/material.dart';
import '../models/map_focus_mode.dart';
import '../theme/ful_theme.dart';

class TopSearchBar extends StatelessWidget {
  final VoidCallback onMenuTap;
  final VoidCallback onSearchTap;
  final VoidCallback onGarageTap;
  final String selectedFuel;
  final MapFocusMode focusMode;
  final bool isDark;

  const TopSearchBar({
    super.key,
    required this.onMenuTap,
    required this.onSearchTap,
    required this.onGarageTap,
    this.selectedFuel = 'Kursunsuz 95',
    this.focusMode = MapFocusMode.smart,
    this.isDark = false,
  });

  @override
  Widget build(BuildContext context) {
    // isDark — parametreden geliyor, Theme.of(context) kullanmıyoruz
    final surface = isDark ? FulColors.darkSurface : FulColors.lightSurface;
    final textColor = isDark ? FulColors.darkText : FulColors.lightText;
    final mutedText =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0),
      child: Container(
        height: 56,
        decoration: BoxDecoration(
          color: surface,
          borderRadius: BorderRadius.circular(28),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.4 : 0.10),
              blurRadius: 20,
              offset: const Offset(0, 6),
              spreadRadius: -2,
            ),
          ],
        ),
        child: Row(
          children: [
            // Menü butonu
            GestureDetector(
              onTap: onMenuTap,
              child: Container(
                width: 48,
                height: 56,
                alignment: Alignment.center,
                child: Icon(
                  Icons.menu_rounded,
                  size: 22,
                  color: textColor,
                ),
              ),
            ),

            // Arama alanı
            Expanded(
              child: GestureDetector(
                onTap: onSearchTap,
                behavior: HitTestBehavior.opaque,
                child: Row(
                  children: [
                    Icon(
                      Icons.search_rounded,
                      size: 18,
                      color: mutedText,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'İstasyon veya şehir ara...',
                        style: TextStyle(
                          fontSize: 14,
                          color: mutedText,
                          fontWeight: FontWeight.w500,
                          fontFamily: 'Outfit',
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            _FocusBadge(mode: focusMode, isDark: isDark),

            // Garajım butonu — araba ikonu ve "Garajım" yazısıyla tıklanabilir
            GestureDetector(
              onTap: onGarageTap,
              child: Container(
                margin: const EdgeInsets.symmetric(vertical: 9, horizontal: 6),
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: FulColors.primary.withOpacity(isDark ? 0.25 : 0.12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: FulColors.primary.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.directions_car_rounded,
                      size: 14,
                      color: FulColors.primary,
                    ),
                    SizedBox(width: 4),
                    Text(
                      'Garajım',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: FulColors.primary,
                        fontFamily: 'Outfit',
                      ),
                    ),
                    SizedBox(width: 2),
                    Icon(
                      Icons.expand_more_rounded,
                      size: 14,
                      color: FulColors.primary,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 4),
          ],
        ),
      ),
    );
  }
}

class _FocusBadge extends StatelessWidget {
  final MapFocusMode mode;
  final bool isDark;

  const _FocusBadge({
    required this.mode,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (mode) {
      MapFocusMode.smart => ('Akıllı', FulColors.logical),
      MapFocusMode.cheapest => ('Ucuz', FulColors.cheapest),
      MapFocusMode.nearest => ('Yakın', FulColors.nearest),
    };
    return Container(
      margin: const EdgeInsets.only(left: 6),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(isDark ? 0.20 : 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontFamily: 'Outfit',
          fontSize: 11,
          fontWeight: FontWeight.w800,
          color: color,
        ),
      ),
    );
  }
}
