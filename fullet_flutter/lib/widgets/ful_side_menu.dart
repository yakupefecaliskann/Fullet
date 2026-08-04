import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/map_focus_mode.dart';
import '../models/news_item.dart';
import '../models/station.dart';
import '../theme/ful_theme.dart';
import 'favorite_station_tile.dart';

/// Trugo tarzı sol yan panel — harita sağda görünmeye devam eder.
/// Scaffold Drawer değil, Stack içinde Overlay olarak kullanılır.
class FulSideMenu extends StatelessWidget {
  final bool isOpen;
  final bool isDark;
  final VoidCallback onClose;
  final MapFocusMode focusMode;
  final void Function(MapFocusMode) onFocusModeChanged;
  final List<NewsItem> news;
  final int stationCount;
  final String appVersion;
  final List<Station> allStations;
  final Set<String> favoriteStationIds;
  final String selectedFuel;
  final void Function(Station) onStationSelected;
  final User? currentUser;
  final Future<void> Function()? onSignIn;
  final Future<void> Function()? onSignOut;
  final VoidCallback? onSettingsTap;

  const FulSideMenu({
    super.key,
    required this.isOpen,
    required this.isDark,
    required this.onClose,
    required this.focusMode,
    required this.onFocusModeChanged,
    required this.news,
    required this.stationCount,
    required this.appVersion,
    required this.allStations,
    required this.favoriteStationIds,
    required this.selectedFuel,
    required this.onStationSelected,
    this.currentUser,
    this.onSignIn,
    this.onSignOut,
    this.onSettingsTap,
  });

  @override
  Widget build(BuildContext context) {
    // isDark parametreden geliyor — Theme.of(context) kullanmıyoruz
    // çünkü MaterialApp teması hiç dark olmaz, sadece harita stili değişiyor
    final surface = isDark ? const Color(0xFF0F1117) : Colors.white;
    final border = isDark ? FulColors.darkBorder : FulColors.lightBorder;
    final textColor = isDark ? FulColors.darkText : FulColors.lightText;
    final mutedColor =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;
    final cardBg = isDark ? const Color(0xFF1A1D27) : const Color(0xFFF7F8FA);

    final screenW = MediaQuery.of(context).size.width;
    final menuW = (screenW * 0.72).clamp(0.0, 300.0);

    return Stack(
      children: [
        // Karanlık overlay (harita tarafı — dokununca kapanır)
        IgnorePointer(
          ignoring: !isOpen,
          child: AnimatedOpacity(
            duration: const Duration(milliseconds: 300),
            opacity: isOpen ? 1.0 : 0.0,
            child: GestureDetector(
              onTap: onClose,
              child: Container(color: Colors.black.withValues(alpha: 0.45)),
            ),
          ),
        ),

        // Menü paneli
        AnimatedPositioned(
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
          top: 0,
          bottom: 0,
          left: isOpen ? 0 : -menuW - 20, // Kapalıyken ekranın dışına kayar
          width: menuW,
          child: ClipRRect(
            borderRadius:
                const BorderRadius.horizontal(right: Radius.circular(28)),
            child: Container(
              // Sadece düz renk — BackdropFilter + opacity kombinasyonu temayı bozuyordu
              color: surface,
              child: Column(
                children: [
                  // ── Header ──
                  _MenuHeader(
                    isDark: isDark,
                    textColor: textColor,
                    mutedColor: mutedColor,
                    border: border,
                    stationCount: stationCount,
                    appVersion: appVersion,
                  ),

                  // ── Menü öğeleri ──
                  Expanded(
                    child: SingleChildScrollView(
                      // Panel top:0/bottom:0 ile tam ekran; edge-to-edge'de son
                      // menü öğesi sistem navigasyon çubuğunun altında kalmasın
                      // diye alt boşluğa inset ekleniyor (başlık zaten
                      // padding.top kullanıyor).
                      padding: EdgeInsets.fromLTRB(16, 16, 16,
                          16 + MediaQuery.of(context).viewPadding.bottom),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Hesap bölümü
                          AccountSection(
                            currentUser: currentUser,
                            onSignIn: onSignIn,
                            onSignOut: onSignOut,
                            isDark: isDark,
                            textColor: textColor,
                            mutedColor: mutedColor,
                            cardBg: cardBg,
                            border: border,
                          ),
                          const SizedBox(height: 16),

                          // Odak Modu bölümü
                          _SectionLabel('HARİTA MODU', mutedColor),
                          const SizedBox(height: 8),
                          _FocusModeCard(
                            currentMode: focusMode,
                            onChanged: onFocusModeChanged,
                            isDark: isDark,
                            cardBg: cardBg,
                            border: border,
                            textColor: textColor,
                          ),

                          const SizedBox(height: 16),
                          _SectionLabel('UYGULAMA', mutedColor),
                          const SizedBox(height: 8),

                          _MenuItem(
                            icon: Icons.settings_outlined,
                            label: 'Ayarlar',
                            isDark: isDark,
                            textColor: textColor,
                            mutedColor: mutedColor,
                            cardBg: cardBg,
                            border: border,
                            onTap: onSettingsTap,
                          ),
                          const SizedBox(height: 8),
                          _MenuItem(
                            icon: Icons.info_outline_rounded,
                            label: 'Hakkında',
                            isDark: isDark,
                            textColor: textColor,
                            mutedColor: mutedColor,
                            cardBg: cardBg,
                            border: border,
                            onTap: () {
                              _showAboutSheet(context, appVersion, isDark,
                                  textColor, mutedColor, cardBg, border);
                            },
                          ),

                          Builder(builder: (context) {
                            final favStations = allStations
                                .where((s) =>
                                    favoriteStationIds.contains(s.id))
                                .toList();
                            if (favStations.isEmpty) {
                              return const SizedBox.shrink();
                            }
                            final visible = favStations.take(5).toList();
                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 16),
                                _SectionLabel('FAVORİLERİM', mutedColor),
                                const SizedBox(height: 8),
                                ...visible.map((station) =>
                                    FavoriteStationTile(
                                      station: station,
                                      selectedFuel: selectedFuel,
                                      onTap: () {
                                        onClose();
                                        onStationSelected(station);
                                      },
                                      isDark: isDark,
                                      textColor: textColor,
                                      mutedColor: mutedColor,
                                      cardBg: cardBg,
                                      border: border,
                                    )),
                                if (favStations.length > 5)
                                  TextButton(
                                    onPressed: () => _showAllFavorites(
                                      context,
                                      favStations,
                                      isDark,
                                      textColor,
                                      mutedColor,
                                      cardBg,
                                      border,
                                    ),
                                    style: TextButton.styleFrom(
                                      padding: EdgeInsets.zero,
                                      minimumSize: Size.zero,
                                      tapTargetSize:
                                          MaterialTapTargetSize.shrinkWrap,
                                    ),
                                    child: Text(
                                      'Tümünü gör (${favStations.length})',
                                      style: const TextStyle(
                                        fontFamily: 'Outfit',
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: FulColors.primary,
                                      ),
                                    ),
                                  ),
                              ],
                            );
                          }),

                          if (news.isNotEmpty) ...[
                            const SizedBox(height: 16),
                            _SectionLabel('SON HABERLER', mutedColor),
                            const SizedBox(height: 8),
                            ...news.take(4).map((n) => _NewsCard(
                                  item: n,
                                  isDark: isDark,
                                  textColor: textColor,
                                  mutedColor: mutedColor,
                                  cardBg: cardBg,
                                  border: border,
                                )),
                          ],
                        ],
                      ),
                    ),
                  ),

                  // ── Alt bilgi ──
                  Container(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
                    decoration: BoxDecoration(
                      border: Border(top: BorderSide(color: border, width: 1)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.local_gas_station_rounded,
                            size: 13, color: FulColors.primary),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            '$stationCount istasyon • Fiyatlar kamudan alınır',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 10,
                              color: mutedColor,
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
      ],
    );
  }

  void _showAboutSheet(BuildContext context, String version, bool isDark,
      Color textColor, Color mutedColor, Color cardBg, Color border) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (_) => AboutSheet(
        version: version,
        isDark: isDark,
        textColor: textColor,
        mutedColor: mutedColor,
        cardBg: cardBg,
        border: border,
      ),
    );
  }

  void _showAllFavorites(
    BuildContext context,
    List<Station> stations,
    bool isDark,
    Color textColor,
    Color mutedColor,
    Color cardBg,
    Color border,
  ) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (_) => _AllFavoritesSheet(
        stations: stations,
        selectedFuel: selectedFuel,
        onStationSelected: (station) {
          Navigator.pop(context);
          onClose();
          onStationSelected(station);
        },
        isDark: isDark,
        textColor: textColor,
        mutedColor: mutedColor,
        cardBg: cardBg,
        border: border,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────
// Hakkında Sayfası (Play Store Uyumlu)
// ─────────────────────────────────────────────────────────────
class AboutSheet extends StatelessWidget {
  final String version;
  final bool isDark;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const AboutSheet({
    super.key,
    required this.version,
    required this.isDark,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  Widget build(BuildContext context) {
    final bg = isDark ? const Color(0xFF0F1117) : Colors.white;
    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 36),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(bottom: 24),
            decoration: BoxDecoration(
              color: border,
              borderRadius: BorderRadius.circular(99),
            ),
          ),

          // Logo + İsim
          Row(
            children: [
              SizedBox(
                width: 64,
                height: 64,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Image.asset(
                    'assets/brand/fullet_play_icon_512.png',
                    fit: BoxFit.cover,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Fullet',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        color: textColor,
                        height: 1,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Türkiye Yakıt Fiyatları',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 13,
                        color: FulColors.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Sürüm $version',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 11,
                        color: mutedColor,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Açıklama kutusu
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: cardBg,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Text(
              'Fullet, Türkiye genelindeki akaryakıt istasyonlarının güncel fiyatlarını harita üzerinde gösteren bağımsız bir uygulamadır.\n\n'
              'Tüm fiyat verileri, petrol şirketlerinin resmi kaynaklarından otomatik olarak derlenmektedir. Herhangi bir istasyon zinciri veya yakıt şirketiyle ticari bağlantımız bulunmamaktadır.',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 13,
                color: textColor,
                height: 1.7,
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Linkler
          _AboutLinkTile(
            icon: Icons.privacy_tip_outlined,
            label: 'Gizlilik Politikası',
            url: 'https://yakupefecaliskann.github.io/Fullet/privacy.html',
            isDark: isDark,
            textColor: textColor,
            cardBg: cardBg,
          ),
          const SizedBox(height: 8),
          _AboutLinkTile(
            icon: Icons.description_outlined,
            label: 'Kullanım Koşulları',
            url: 'https://yakupefecaliskann.github.io/Fullet/terms.html',
            isDark: isDark,
            textColor: textColor,
            cardBg: cardBg,
          ),
          const SizedBox(height: 8),
          _AboutLinkTile(
            icon: Icons.mail_outline_rounded,
            label: 'İletişim: fulletapp@gmail.com',
            url: 'mailto:fulletapp@gmail.com',
            isDark: isDark,
            textColor: textColor,
            cardBg: cardBg,
          ),

          const SizedBox(height: 20),

          Text(
            '© 2026 Fullet — Tüm hakları saklıdır.',
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 11,
              color: mutedColor,
            ),
          ),
        ],
      ),
    );
  }
}

class _AboutLinkTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String url;
  final bool isDark;
  final Color textColor;
  final Color cardBg;

  const _AboutLinkTile({
    required this.icon,
    required this.label,
    required this.url,
    required this.isDark,
    required this.textColor,
    required this.cardBg,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () async {
        HapticFeedback.lightImpact();
        final uri = Uri.parse(url);
        if (await canLaunchUrl(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Icon(icon, color: FulColors.primary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: textColor,
                ),
              ),
            ),
            Icon(Icons.open_in_new_rounded,
                size: 16,
                color: isDark
                    ? FulColors.darkTextMuted
                    : FulColors.lightTextMuted),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────
// Header
// ─────────────────────────────────────────────────────────────
class _MenuHeader extends StatelessWidget {
  final bool isDark;
  final Color textColor;
  final Color mutedColor;
  final Color border;
  final int stationCount;
  final String appVersion;

  const _MenuHeader({
    required this.isDark,
    required this.textColor,
    required this.mutedColor,
    required this.border,
    required this.stationCount,
    required this.appVersion,
  });

  @override
  Widget build(BuildContext context) {
    final topPad = MediaQuery.of(context).padding.top;
    return Container(
      padding: EdgeInsets.fromLTRB(20, topPad + 20, 20, 20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            FulColors.primary.withValues(alpha: isDark ? 0.18 : 0.08),
            Colors.transparent,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border(
          bottom: BorderSide(color: border, width: 1),
        ),
      ),
      child: Row(
        children: [
          // Logo
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [FulColors.primary, FulColors.primaryDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.15),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.asset(
                'assets/brand/fullet_play_icon_512.png',
                fit: BoxFit.cover,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      'Fullet',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontWeight: FontWeight.w900,
                        fontSize: 24,
                        color: textColor,
                        height: 1,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: FulColors.primary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        'v$appVersion',
                        style: const TextStyle(
                          fontFamily: 'Outfit',
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: FulColors.primary,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  'Türkiye Yakıt Fiyatları',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 12,
                    color: mutedColor,
                    fontWeight: FontWeight.w500,
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

// ─────────────────────────────────────────────────────────────
// Odak Modu Kartı
// ─────────────────────────────────────────────────────────────
class _FocusModeCard extends StatelessWidget {
  final MapFocusMode currentMode;
  final void Function(MapFocusMode) onChanged;
  final bool isDark;
  final Color cardBg;
  final Color border;
  final Color textColor;

  const _FocusModeCard({
    required this.currentMode,
    required this.onChanged,
    required this.isDark,
    required this.cardBg,
    required this.border,
    required this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border),
      ),
      child: Column(
        children: [
          _ModeOption(
            mode: MapFocusMode.smart,
            icon: Icons.auto_awesome_rounded,
            label: 'Akıllı',
            sub: 'Uzaklık + Fiyat dengesi',
            color: FulColors.logical,
            current: currentMode,
            onTap: () {
              HapticFeedback.lightImpact();
              onChanged(MapFocusMode.smart);
            },
            isDark: isDark,
            textColor: textColor,
            isFirst: true,
          ),
          Divider(height: 1, color: border),
          _ModeOption(
            mode: MapFocusMode.cheapest,
            icon: Icons.savings_rounded,
            label: 'En Ucuz',
            sub: 'Litre başına en düşük fiyat',
            color: FulColors.cheapest,
            current: currentMode,
            onTap: () {
              HapticFeedback.lightImpact();
              onChanged(MapFocusMode.cheapest);
            },
            isDark: isDark,
            textColor: textColor,
          ),
          Divider(height: 1, color: border),
          _ModeOption(
            mode: MapFocusMode.nearest,
            icon: Icons.near_me_rounded,
            label: 'En Yakın',
            sub: 'Kuş uçuşu mesafe',
            color: FulColors.nearest,
            current: currentMode,
            onTap: () {
              HapticFeedback.lightImpact();
              onChanged(MapFocusMode.nearest);
            },
            isDark: isDark,
            textColor: textColor,
            isLast: true,
          ),
        ],
      ),
    );
  }
}

class _ModeOption extends StatelessWidget {
  final MapFocusMode mode;
  final IconData icon;
  final String label;
  final String sub;
  final Color color;
  final MapFocusMode current;
  final VoidCallback onTap;
  final bool isDark;
  final Color textColor;
  final bool isFirst;
  final bool isLast;

  const _ModeOption({
    required this.mode,
    required this.icon,
    required this.label,
    required this.sub,
    required this.color,
    required this.current,
    required this.onTap,
    required this.isDark,
    required this.textColor,
    this.isFirst = false,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    final isSelected = mode == current;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.1) : Colors.transparent,
          borderRadius: BorderRadius.vertical(
            top: isFirst ? const Radius.circular(15) : Radius.zero,
            bottom: isLast ? const Radius.circular(15) : Radius.zero,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: isSelected ? color : color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon,
                  color: isSelected ? Colors.white : color, size: 18),
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
                      fontSize: 14,
                      color: isSelected ? color : textColor,
                    ),
                  ),
                  Text(
                    sub,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 11,
                      color: isDark
                          ? FulColors.darkTextMuted
                          : FulColors.lightTextMuted,
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(Icons.check_circle_rounded, color: color, size: 18),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────
// Yardımcı Widget'lar
// ─────────────────────────────────────────────────────────────
class _SectionLabel extends StatelessWidget {
  final String text;
  final Color color;
  const _SectionLabel(this.text, this.color);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: TextStyle(
        fontFamily: 'Outfit',
        fontSize: 10,
        fontWeight: FontWeight.w700,
        color: color,
        letterSpacing: 1.2,
      ),
    );
  }
}

class _MenuItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isDark;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;
  final VoidCallback? onTap;

  const _MenuItem({
    required this.icon,
    required this.label,
    required this.isDark,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap?.call();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Icon(icon, color: FulColors.primary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontWeight: FontWeight.w700,
                  fontSize: 14,
                  color: textColor,
                ),
              ),
            ),
            Icon(Icons.chevron_right_rounded,
                size: 18,
                color: isDark
                    ? FulColors.darkTextMuted
                    : FulColors.lightTextMuted),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────
// Haber Kartı — Tıklanabilir + Gelişmiş Tasarım
// ─────────────────────────────────────────────────────────────
class _NewsCard extends StatelessWidget {
  final NewsItem item;
  final bool isDark;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const _NewsCard({
    required this.item,
    required this.isDark,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  Widget build(BuildContext context) {
    final hasLink = item.link.isNotEmpty;
    return GestureDetector(
      onTap: hasLink
          ? () async {
              HapticFeedback.lightImpact();
              final uri = Uri.parse(item.link);
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              }
            }
          : null,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: cardBg,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Kaynak + Tarih çipi
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: FulColors.primary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(99),
                  ),
                  child: Text(
                    item.source,
                    style: const TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: FulColors.primary,
                    ),
                  ),
                ),
                if (item.date != null) ...[
                  const SizedBox(width: 6),
                  Text(
                    _formatDate(item.date!),
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 10,
                      color: mutedColor,
                    ),
                  ),
                ],
                const Spacer(),
                if (hasLink)
                  Icon(Icons.open_in_new_rounded, size: 14, color: mutedColor),
              ],
            ),
            const SizedBox(height: 8),
            // Başlık
            Text(
              item.title,
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: textColor,
                height: 1.45,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime d) {
    final now = DateTime.now();
    final diff = now.difference(d);
    if (diff.inDays == 0) return 'Bugün';
    if (diff.inDays == 1) return 'Dün';
    if (diff.inDays < 7) return '${diff.inDays} gün önce';
    return '${d.day}.${d.month.toString().padLeft(2, '0')}.${d.year}';
  }
}

// ─────────────────────────────────────────────────────────────
// Hesap Bölümü
// ─────────────────────────────────────────────────────────────
class AccountSection extends StatefulWidget {
  final User? currentUser;
  final Future<void> Function()? onSignIn;
  final Future<void> Function()? onSignOut;
  final bool isDark;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const AccountSection({
    super.key,
    required this.currentUser,
    required this.onSignIn,
    required this.onSignOut,
    required this.isDark,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  State<AccountSection> createState() => AccountSectionState();
}

class AccountSectionState extends State<AccountSection> {
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    if (widget.currentUser != null) {
      return _buildSignedIn();
    }
    return _buildSignedOut();
  }

  Widget _buildSignedIn() {
    final user = widget.currentUser!;
    final name = user.displayName ?? 'Kullanıcı';
    final email = user.email ?? '';
    final photoUrl = user.photoURL;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: widget.cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: widget.border),
      ),
      child: Row(
        children: [
          // Avatar
          CircleAvatar(
            radius: 22,
            backgroundColor: FulColors.primary.withValues(alpha: 0.15),
            backgroundImage:
                photoUrl != null ? NetworkImage(photoUrl) : null,
            child: photoUrl == null
                ? Text(
                    name.isNotEmpty ? name[0].toUpperCase() : 'K',
                    style: const TextStyle(
                      fontFamily: 'Outfit',
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                      color: FulColors.primary,
                    ),
                  )
                : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                    color: widget.textColor,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (email.isNotEmpty)
                  Text(
                    email,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 11,
                      color: widget.mutedColor,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
          // Çıkış butonu
          GestureDetector(
            onTap: _loading ? null : _signOut,
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: widget.isDark
                    ? Colors.white.withValues(alpha: 0.06)
                    : Colors.black.withValues(alpha: 0.04),
                borderRadius: BorderRadius.circular(10),
              ),
              child: _loading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: FulColors.primary),
                    )
                  : Icon(Icons.logout_rounded,
                      size: 18, color: widget.mutedColor),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSignedOut() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: widget.cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: widget.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: FulColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.cloud_done_rounded,
                    size: 18, color: FulColors.primary),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Hesabınızı kaydedin',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                    color: widget.textColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Favorileriniz cihazlar arasında senkronize edilsin.',
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 12,
              color: widget.mutedColor,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: GestureDetector(
              onTap: _loading ? null : _signIn,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                padding: const EdgeInsets.symmetric(vertical: 11),
                decoration: BoxDecoration(
                  color: _loading
                      ? FulColors.primary.withValues(alpha: 0.7)
                      : FulColors.primary,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: _loading
                    ? const Center(
                        child: SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        ),
                      )
                    : const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.g_mobiledata_rounded,
                              color: Colors.white, size: 22),
                          SizedBox(width: 6),
                          Text(
                            'Google ile Giriş Yap',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontWeight: FontWeight.w800,
                              fontSize: 13,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _signIn() async {
    setState(() => _loading = true);
    try {
      await widget.onSignIn?.call();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _signOut() async {
    setState(() => _loading = true);
    try {
      await widget.onSignOut?.call();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
}

// ─────────────────────────────────────────────────────────────
// Tüm Favoriler Sayfası
// ─────────────────────────────────────────────────────────────
class _AllFavoritesSheet extends StatelessWidget {
  final List<Station> stations;
  final String selectedFuel;
  final void Function(Station) onStationSelected;
  final bool isDark;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const _AllFavoritesSheet({
    required this.stations,
    required this.selectedFuel,
    required this.onStationSelected,
    required this.isDark,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  Widget build(BuildContext context) {
    final bg = isDark ? const Color(0xFF0F1117) : Colors.white;
    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 36),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
              color: border,
              borderRadius: BorderRadius.circular(99),
            ),
          ),
          Row(
            children: [
              const Icon(
                Icons.favorite_rounded,
                size: 18,
                color: FulColors.primary,
              ),
              const SizedBox(width: 8),
              Text(
                'Favorilerim',
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                  color: textColor,
                ),
              ),
              const Spacer(),
              Text(
                '${stations.length} istasyon',
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 12,
                  color: mutedColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.55,
            ),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: stations.length,
              itemBuilder: (_, i) => FavoriteStationTile(
                station: stations[i],
                selectedFuel: selectedFuel,
                onTap: () => onStationSelected(stations[i]),
                isDark: isDark,
                textColor: textColor,
                mutedColor: mutedColor,
                cardBg: cardBg,
                border: border,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
