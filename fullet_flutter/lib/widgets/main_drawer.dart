import 'package:flutter/material.dart';
import '../models/news_item.dart';
import '../models/map_focus_mode.dart';
import '../theme/ful_theme.dart';

class MainDrawer extends StatelessWidget {
  final MapFocusMode focusMode;
  final Set<String> selectedBrands;
  final List<String> brandOrder;
  final List<NewsItem> news;
  final String Function(MapFocusMode mode) modeLabel;
  final IconData Function(MapFocusMode mode) modeIcon;
  final String Function(String brand) brandShortName;
  final Color Function(String brand) brandColor;
  final ValueChanged<MapFocusMode> onModeChanged;
  final ValueChanged<String> onBrandToggled;
  final VoidCallback onClearBrands;
  final ValueChanged<NewsItem> onNewsTap;
  final VoidCallback onPrivacyTap;

  const MainDrawer({
    super.key,
    required this.focusMode,
    required this.selectedBrands,
    required this.brandOrder,
    required this.news,
    required this.modeLabel,
    required this.modeIcon,
    required this.brandShortName,
    required this.brandColor,
    required this.onModeChanged,
    required this.onBrandToggled,
    required this.onClearBrands,
    required this.onNewsTap,
    required this.onPrivacyTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? FulColors.darkSurface : FulColors.lightSurface;
    final cardBg = isDark ? FulColors.darkCard : FulColors.lightCard;
    final border = isDark ? FulColors.darkBorder : FulColors.lightBorder;
    final textColor = isDark ? FulColors.darkText : FulColors.lightText;
    final mutedColor =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;

    return Drawer(
      backgroundColor: bg,
      width: MediaQuery.of(context).size.width * 0.82,
      child: SafeArea(
        child: Column(
          children: [
            // --- Header ---
            Container(
              padding: const EdgeInsets.fromLTRB(20, 20, 12, 20),
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(color: border, width: 1),
                ),
              ),
              child: Row(
                children: [
                  // Logo + isim
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [FulColors.primary, FulColors.cheapest],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(
                      Icons.local_gas_station_rounded,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Fullet',
                        style: TextStyle(
                          fontFamily: 'Outfit',
                          fontWeight: FontWeight.w900,
                          fontSize: 20,
                          color: textColor,
                        ),
                      ),
                      Text(
                        'Akaryakıt Fiyatları',
                        style: TextStyle(
                          fontFamily: 'Outfit',
                          fontWeight: FontWeight.w500,
                          fontSize: 11,
                          color: mutedColor,
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  IconButton(
                    icon: Icon(Icons.close_rounded, color: mutedColor),
                    onPressed: () => Navigator.pop(context),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(
                      minWidth: 36,
                      minHeight: 36,
                    ),
                  ),
                ],
              ),
            ),

            // --- İçerik ---
            Expanded(
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Sıralama modu
                    _sectionLabel('Harita Sıralaması', mutedColor),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: cardBg,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        children: MapFocusMode.values
                            .map((mode) => Expanded(
                                  child: _modeButton(
                                      context, mode, isDark, textColor),
                                ))
                            .toList(),
                      ),
                    ),

                    const SizedBox(height: 8),

                    // Aktif mod açıklaması
                    _modeLegend(context, isDark, mutedColor),

                    const SizedBox(height: 24),

                    // Marka filtresi
                    Row(
                      children: [
                        _sectionLabel('Markalar', mutedColor),
                        const Spacer(),
                        if (selectedBrands.isNotEmpty)
                          GestureDetector(
                            onTap: onClearBrands,
                            child: const Text(
                              'Tümünü Göster',
                              style: TextStyle(
                                color: FulColors.primary,
                                fontWeight: FontWeight.w700,
                                fontSize: 12,
                                fontFamily: 'Outfit',
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children:
                          brandOrder.map((b) => _brandChip(b, isDark)).toList(),
                    ),

                    const SizedBox(height: 28),

                    // Haberler
                    _sectionLabel('Piyasa Haberleri', mutedColor),
                    const SizedBox(height: 10),
                    if (news.isEmpty)
                      Padding(
                        padding: const EdgeInsets.all(12),
                        child: Text(
                          'Güncel haber bulunmuyor.',
                          style: TextStyle(
                              color: mutedColor,
                              fontSize: 13,
                              fontFamily: 'Outfit'),
                        ),
                      )
                    else
                      ...news.take(5).map((item) => _newsTile(
                          item, isDark, border, textColor, mutedColor)),

                    const SizedBox(height: 24),

                    // Hakkında
                    _sectionLabel('Hakkında', mutedColor),
                    const SizedBox(height: 10),
                    _privacyTile(isDark, cardBg, border, textColor, mutedColor),
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionLabel(String text, Color color) {
    return Text(
      text.toUpperCase(),
      style: TextStyle(
        fontFamily: 'Outfit',
        fontWeight: FontWeight.w800,
        fontSize: 11,
        letterSpacing: 1.2,
        color: color,
      ),
    );
  }

  Widget _modeButton(
      BuildContext context, MapFocusMode mode, bool isDark, Color textColor) {
    final isSelected = focusMode == mode;

    final Color accent;
    switch (mode) {
      case MapFocusMode.smart:
        accent = FulColors.logical;
        break;
      case MapFocusMode.cheapest:
        accent = FulColors.cheapest;
        break;
      case MapFocusMode.nearest:
        accent = FulColors.nearest;
        break;
    }

    return GestureDetector(
      onTap: () => onModeChanged(mode),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? accent : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: accent.withOpacity(0.40),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  )
                ]
              : null,
        ),
        child: Column(
          children: [
            Icon(
              modeIcon(mode),
              size: 20,
              color: isSelected
                  ? Colors.white
                  : (isDark
                      ? FulColors.darkTextMuted
                      : FulColors.lightTextMuted),
            ),
            const SizedBox(height: 4),
            Text(
              modeLabel(mode),
              style: TextStyle(
                fontFamily: 'Outfit',
                color: isSelected
                    ? Colors.white
                    : (isDark
                        ? FulColors.darkTextMuted
                        : FulColors.lightTextMuted),
                fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _modeLegend(BuildContext context, bool isDark, Color mutedColor) {
    final String desc;
    final Color accent;
    final IconData icon;
    switch (focusMode) {
      case MapFocusMode.smart:
        desc =
            'Yakınlık + fiyat dengesini hesaplar. Gitmeye değer en iyi istasyonu öne çıkarır.';
        accent = FulColors.logical;
        icon = Icons.auto_awesome_rounded;
        break;
      case MapFocusMode.cheapest:
        desc = 'Seçili yakıt için en düşük fiyatlı istasyonları öne çıkarır.';
        accent = FulColors.cheapest;
        icon = Icons.trending_down_rounded;
        break;
      case MapFocusMode.nearest:
        desc = 'Bulunduğun konuma en yakın istasyonları öne çıkarır.';
        accent = FulColors.nearest;
        icon = Icons.near_me_rounded;
        break;
    }
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 250),
      child: Container(
        key: ValueKey(focusMode),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: accent.withOpacity(isDark ? 0.15 : 0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: accent.withOpacity(0.25)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 16, color: accent),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                desc,
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 12,
                  color: mutedColor,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _brandChip(String brand, bool isDark) {
    final isSelected = selectedBrands.contains(brand);
    final color = brandColor(brand);
    return GestureDetector(
      onTap: () => onBrandToggled(brand),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? color : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: isSelected
                ? color
                : (isDark ? FulColors.darkBorder : FulColors.lightBorder),
            width: 1.5,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: color.withOpacity(0.40),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  )
                ]
              : null,
        ),
        child: Text(
          brandShortName(brand),
          style: TextStyle(
            fontFamily: 'Outfit',
            color: isSelected
                ? Colors.white
                : (isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted),
            fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
    );
  }

  Widget _newsTile(NewsItem item, bool isDark, Color border, Color textColor,
      Color mutedColor) {
    return GestureDetector(
      onTap: () => onNewsTap(item),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: border),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: FulColors.primary.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(
                Icons.article_rounded,
                color: FulColors.primary,
                size: 18,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                      color: textColor,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${item.source} • ${item.date}',
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      color: mutedColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios_rounded, size: 12, color: mutedColor),
          ],
        ),
      ),
    );
  }

  Widget _privacyTile(bool isDark, Color cardBg, Color border, Color textColor,
      Color mutedColor) {
    return GestureDetector(
      onTap: onPrivacyTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: border),
        ),
        child: Row(
          children: [
            const Icon(Icons.shield_outlined,
                size: 20, color: FulColors.primary),
            const SizedBox(width: 12),
            Text(
              'Gizlilik Politikası',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontWeight: FontWeight.w700,
                fontSize: 14,
                color: textColor,
              ),
            ),
            const Spacer(),
            Icon(Icons.arrow_forward_ios_rounded, size: 13, color: mutedColor),
          ],
        ),
      ),
    );
  }
}
