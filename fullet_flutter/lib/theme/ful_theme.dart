import 'package:flutter/material.dart';

/// Fullet Tasarım Sistemi — Merkezi renk, tipografi ve stil tokenları.
/// Tüm widget'lar buradan renk alır, hiçbir yerde hardcoded renk olmaz.
abstract final class FulColors {
  // --- Marka Rengi ---
  static const primary = Color(0xFF0D9488); // Derin Teal
  static const primaryDark = Color(0xFF0A7167);
  static const primaryLight = Color(0xFF14B8A6);

  // --- Sıralama Renkleri ---
  static const logical = Color(0xFF0D9488); // En mantıklı → Derin Teal
  static const cheapest = Color(0xFF3B82F6); // En ucuz → Mavi
  static const nearest = Color(0xFFF59E0B); // En yakın → Amber

  // --- Fiyat Durumu ---
  static const priceFresh = Color(0xFF22C55E); // Taze fiyat
  static const priceStale = Color(0xFFF59E0B); // Eski fiyat
  static const priceUnknown = Color(0xFF9CA3AF); // Bilinmiyor

  // --- Light Tema ---
  static const lightBackground = Color(0xFFF8FAFC);
  static const lightSurface = Color(0xFFFFFFFF);
  static const lightCard = Color(0xFFF1F5F9);
  static const lightBorder = Color(0xFFE2E8F0);
  static const lightText = Color(0xFF0F172A);
  static const lightTextMuted = Color(0xFF64748B);

  // --- Dark Tema ---
  static const darkBackground = Color(0xFF0B0F19);
  static const darkSurface = Color(0xFF141925);
  static const darkCard = Color(0xFF1E2535);
  static const darkBorder = Color(0xFF2A3348);
  static const darkText = Color(0xFFF1F5F9);
  static const darkTextMuted = Color(0xFF94A3B8);

  // --- Marka Renkleri ---
  static const shell = Color(0xFFFFCC00);
  static const shellRed = Color(0xFFD6001C);
  static const opet = Color(0xFF004797);
  static const petrolOfisi = Color(0xFFE30613);
  static const bp = Color(0xFF009B3A);
  static const totalEnergies = Color(0xFF005BBB);
  static const tp = Color(0xFF00A3A3);
  static const aytemiz = Color(0xFFFF7A00);

  // --- Semantik ---
  static const success = Color(0xFF22C55E);
  static const danger = Color(0xFFEF4444);
  static const warning = Color(0xFFF59E0B);
  static const info = Color(0xFF3B82F6);
}

abstract final class FulTheme {
  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: const ColorScheme.light(
        primary: FulColors.primary,
        onPrimary: Colors.white,
        secondary: FulColors.cheapest,
        surface: FulColors.lightSurface,
        onSurface: FulColors.lightText,
        outline: FulColors.lightBorder,
      ),
      scaffoldBackgroundColor: FulColors.lightBackground,
      fontFamily: 'Outfit',
      textTheme: _textTheme(FulColors.lightText, FulColors.lightTextMuted),
      drawerTheme: const DrawerThemeData(
        backgroundColor: FulColors.lightSurface,
        surfaceTintColor: Colors.transparent,
      ),
      dividerTheme: const DividerThemeData(
        color: FulColors.lightBorder,
        thickness: 1,
      ),
    );
  }

  static ThemeData dark() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary: FulColors.primary,
        onPrimary: FulColors.darkBackground,
        secondary: FulColors.cheapest,
        surface: FulColors.darkSurface,
        onSurface: FulColors.darkText,
        outline: FulColors.darkBorder,
      ),
      scaffoldBackgroundColor: FulColors.darkBackground,
      fontFamily: 'Outfit',
      textTheme: _textTheme(FulColors.darkText, FulColors.darkTextMuted),
      drawerTheme: const DrawerThemeData(
        backgroundColor: FulColors.darkSurface,
        surfaceTintColor: Colors.transparent,
      ),
      dividerTheme: const DividerThemeData(
        color: FulColors.darkBorder,
        thickness: 1,
      ),
    );
  }

  static TextTheme _textTheme(Color primary, Color muted) {
    return TextTheme(
      displayLarge: TextStyle(
          fontFamily: 'Outfit',
          color: primary,
          fontWeight: FontWeight.w900,
          fontSize: 32),
      titleLarge: TextStyle(
          fontFamily: 'Outfit',
          color: primary,
          fontWeight: FontWeight.w800,
          fontSize: 22),
      titleMedium: TextStyle(
          fontFamily: 'Outfit',
          color: primary,
          fontWeight: FontWeight.w700,
          fontSize: 18),
      bodyLarge: TextStyle(
          fontFamily: 'Outfit',
          color: primary,
          fontWeight: FontWeight.w500,
          fontSize: 15),
      bodyMedium: TextStyle(
          fontFamily: 'Outfit',
          color: muted,
          fontWeight: FontWeight.w400,
          fontSize: 13),
      labelSmall: TextStyle(
          fontFamily: 'Outfit',
          color: muted,
          fontWeight: FontWeight.w600,
          fontSize: 11,
          letterSpacing: 0.4),
    );
  }

  /// Harita stili — dark mod için koyu harita JSON
  static String get darkMapStyle => '''
[
  {"elementType": "geometry", "stylers": [{"color": "#0B0F19"}]},
  {"elementType": "labels.text.stroke", "stylers": [{"color": "#0B0F19"}]},
  {"elementType": "labels.text.fill", "stylers": [{"color": "#94A3B8"}]},
  {"featureType": "road", "elementType": "geometry", "stylers": [{"color": "#1E2535"}]},
  {"featureType": "road.highway", "elementType": "geometry", "stylers": [{"color": "#2A3348"}]},
  {"featureType": "road.highway", "elementType": "geometry.stroke", "stylers": [{"color": "#141925"}]},
  {"featureType": "water", "elementType": "geometry", "stylers": [{"color": "#07090F"}]},
  {"featureType": "poi", "stylers": [{"visibility": "off"}]},
  {"featureType": "transit", "stylers": [{"visibility": "off"}]},
  {"featureType": "administrative", "elementType": "geometry.stroke", "stylers": [{"color": "#2A3348"}]},
  {"featureType": "landscape", "elementType": "geometry", "stylers": [{"color": "#0F1520"}]}
]
''';

  /// Harita stili — light mod için temiz harita JSON
  static String get lightMapStyle => '''
[
  {"featureType": "poi", "stylers": [{"visibility": "off"}]},
  {"featureType": "transit", "stylers": [{"visibility": "off"}]},
  {"featureType": "road", "elementType": "labels.icon", "stylers": [{"visibility": "off"}]}
]
''';
}

/// Marka rengi yardımcısı
Color brandColorFor(String brand) {
  switch (brand.trim()) {
    case 'Shell':
      return FulColors.shell;
    case 'Opet':
      return FulColors.opet;
    case 'Petrol Ofisi':
      return FulColors.petrolOfisi;
    case 'BP':
      return FulColors.bp;
    case 'TotalEnergies':
      return FulColors.totalEnergies;
    case 'Türkiye Petrolleri':
    case 'TP':
      return FulColors.tp;
    case 'Aytemiz':
      return FulColors.aytemiz;
    default:
      return FulColors.primary;
  }
}
