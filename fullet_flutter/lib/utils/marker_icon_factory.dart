import 'dart:collection';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class MarkerIconFactory {
  /// H1: Bu önbellek eskiden sınırsızdı ve hiçbir yerde temizlenmiyordu —
  /// gerçek bir bellek sızıntısıydı.
  ///
  /// Anahtar fiyat metnini ve durum bayraklarını içeriyor
  /// (`isCheapest`/`isMostLogical`/`isSelected`), yani **oturum boyunca sürekli
  /// yeni değerler alıyor**: fiyatlar güncellenir, kullanıcı hareket ettikçe taç
  /// istasyon değiştirir, her dokunuş 1.32x ölçekli yeni bir PNG üretir. En kötü
  /// senaryo sürüş modu: her konum güncellemesi tam marker yeniden inşası
  /// tetikliyor, uzun bir yolculukta önbellek monoton büyüyordu. Her giriş
  /// çözülmüş bir `BitmapDescriptor` (124×60, seçiliyken 164×79 PNG).
  ///
  /// Tavan, ekranda aynı anda çizilen marker sayısına göre seçildi:
  /// `_DeclutterConfig` en fazla 110 marker'a izin veriyor, yani 300 giriş
  /// yaklaşık üç ekran dolusu ikonu sıcak tutar — pan/zoom sırasında isabet
  /// oranı korunur, bellek ise sabit kalır.
  static const int _maxCacheEntries = 300;

  /// `LinkedHashMap` ekleme sırasını korur; erişimde girişi silip yeniden
  /// eklemek onu "en yeni" konuma taşır, böylece `keys.first` daima en uzun
  /// süredir kullanılmayan giriştir (LRU).
  static final LinkedHashMap<String, BitmapDescriptor> _cache =
      LinkedHashMap<String, BitmapDescriptor>();

  static BitmapDescriptor? _cacheGet(String key) {
    final cached = _cache.remove(key);
    if (cached != null) {
      _cache[key] = cached;
    }
    return cached;
  }

  static void _cachePut(String key, BitmapDescriptor descriptor) {
    _cache.remove(key);
    _cache[key] = descriptor;
    while (_cache.length > _maxCacheEntries) {
      _cache.remove(_cache.keys.first);
    }
  }

  /// Yalnızca testler için: önbelleği ve sayacını sıfırlar.
  @visibleForTesting
  static void resetCacheForTest() => _cache.clear();

  @visibleForTesting
  static int get cacheLength => _cache.length;

  @visibleForTesting
  static int get maxCacheEntries => _maxCacheEntries;

  @visibleForTesting
  static void putForTest(String key, BitmapDescriptor descriptor) =>
      _cachePut(key, descriptor);

  @visibleForTesting
  static BitmapDescriptor? getForTest(String key) => _cacheGet(key);

  static Future<BitmapDescriptor> stationPrice({
    required String brand,
    required String priceText,
    required bool hasPrice,
    required String priceStatus,
    required bool isCheapest,
    required bool isMostLogical,
    required bool compact,
    bool isSelected = false,
    bool isLowPriority = false,
  }) async {
    final key =
        'price|$brand|$priceText|$hasPrice|$priceStatus|$isCheapest|$isMostLogical|$compact|$isSelected|$isLowPriority';
    final cached = _cacheGet(key);
    if (cached != null) return cached;

    var palette = _paletteFor(
      brand: brand,
      hasPrice: hasPrice,
      priceStatus: priceStatus,
      isCheapest: isCheapest,
      isMostLogical: isMostLogical,
    );
    // Madde 21: `low_priority` = 7 gündür doğrulanmamış kayıt. Silinmez ve
    // gizlenmez (fiyatı hâlâ doğru olabilir) ama görsel olarak geri çekilir;
    // "en ucuz"/"en mantıklı" yarışından da çıkarılmıştır
    // (SmartStationService). Mekanizma bugüne kadar kuruluydu ama hiçbir
    // yere bağlı değildi — uygulama `low_priority`'yi normal gösteriyordu.
    if (isLowPriority) {
      palette = palette.dimmed();
    }

    final bytes = await _drawPriceMarker(
      text: hasPrice ? priceText : '-',
      palette: palette,
      compact: compact,
      isSelected: isSelected,
    );
    // payload for runtime-generated marker PNGs.
    // ignore: deprecated_member_use
    final descriptor = BitmapDescriptor.fromBytes(bytes);
    _cachePut(key, descriptor);
    return descriptor;
  }

  static Future<BitmapDescriptor> cluster({
    required int count,
  }) async {
    final key = 'cluster|$count';
    final cached = _cacheGet(key);
    if (cached != null) return cached;

    final bytes = await _drawClusterMarker(count: count);
    // ignore: deprecated_member_use
    final descriptor = BitmapDescriptor.fromBytes(bytes);
    _cachePut(key, descriptor);
    return descriptor;
  }

  static _MarkerPalette _paletteFor({
    required String brand,
    required bool hasPrice,
    required String priceStatus,
    required bool isCheapest,
    required bool isMostLogical,
  }) {
    if (!hasPrice) {
      return _noPricePaletteFor(brand);
    }

    if (isMostLogical) {
      return const _MarkerPalette(
        background: Color(0xFF0D9488),
        foreground: Colors.white,
        border: Color(0xFF0A7167),
      );
    }

    if (isCheapest) {
      return const _MarkerPalette(
        background: Color(0xFF3B82F6),
        foreground: Colors.white,
        border: Color(0xFF1D4ED8),
      );
    }

    if (priceStatus == 'stale') {
      return const _MarkerPalette(
        background: Color(0xFFF59E0B),
        foreground: Colors.white,
        border: Color(0xFF92400E),
      );
    }

    switch (brand) {
      case 'Shell':
        return const _MarkerPalette(
          background: Color(0xFFFFCC00),
          foreground: Color(0xFFD6001C),
          border: Color(0xFFD6001C),
        );
      case 'Opet':
        return const _MarkerPalette(
          background: Color(0xFF004797),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
      case 'Petrol Ofisi':
        return const _MarkerPalette(
          background: Color(0xFFDF1B25),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
      case 'BP':
        return const _MarkerPalette(
          background: Color(0xFF009900),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
      case 'TotalEnergies':
        return const _MarkerPalette(
          background: Color(0xFFED0000),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
      case 'Aytemiz':
        return const _MarkerPalette(
          background: Color(0xFFF37121),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
      case 'Türkiye Petrolleri':
      case 'Turkiye Petrolleri':
      case 'TP':
        return const _MarkerPalette(
          background: Color(0xFF003087),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
      default:
        return const _MarkerPalette(
          background: Color(0xFF111827),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
    }
  }

  static _MarkerPalette _noPricePaletteFor(String brand) {
    switch (brand) {
      case 'Shell':
        return const _MarkerPalette(
          background: Color(0xFFFFFBEB),
          foreground: Color(0xFFD6001C),
          border: Color(0xFFFFCC00),
        );
      case 'Opet':
        return const _MarkerPalette(
          background: Color(0xFFEFF6FF),
          foreground: Color(0xFF004797),
          border: Color(0xFF004797),
        );
      case 'Petrol Ofisi':
        return const _MarkerPalette(
          background: Color(0xFFFFF1F2),
          foreground: Color(0xFFDF1B25),
          border: Color(0xFFDF1B25),
        );
      case 'BP':
        return const _MarkerPalette(
          background: Color(0xFFF0FDF4),
          foreground: Color(0xFF009900),
          border: Color(0xFF009900),
        );
      case 'TotalEnergies':
        return const _MarkerPalette(
          background: Color(0xFFFFF1F2),
          foreground: Color(0xFFED0000),
          border: Color(0xFFED0000),
        );
      case 'Aytemiz':
        return const _MarkerPalette(
          background: Color(0xFFFFF7ED),
          foreground: Color(0xFFF37121),
          border: Color(0xFFF37121),
        );
      case 'Türkiye Petrolleri':
      case 'Turkiye Petrolleri':
      case 'TP':
        return const _MarkerPalette(
          background: Color(0xFFEFF6FF),
          foreground: Color(0xFF003087),
          border: Color(0xFF003087),
        );
      default:
        return const _MarkerPalette(
          background: Color(0xFFF3F4F6),
          foreground: Color(0xFF6B7280),
          border: Color(0xFFFFFFFF),
        );
    }
  }

  static Future<Uint8List> _drawPriceMarker({
    required String text,
    required _MarkerPalette palette,
    required bool compact,
    bool isSelected = false,
  }) async {
    final scale = isSelected ? 1.32 : 1.0;
    final width = (compact ? 92.0 : 124.0) * scale;
    final height = (compact ? 46.0 : 60.0) * scale;
    const bubbleLeft = 4.0;
    const bubbleTop = 4.0;
    final bubbleWidth = width - 8.0;
    final bubbleHeight = (compact ? 26.0 : 36.0) * scale;
    final radius = (compact ? 8.0 : 11.0) * scale;
    final tipHeight = (compact ? 10.0 : 14.0) * scale;

    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder, Rect.fromLTWH(0, 0, width, height));

    final bubbleRect = Rect.fromLTWH(
      bubbleLeft,
      bubbleTop,
      bubbleWidth,
      bubbleHeight,
    );
    final bubblePath = Path()
      ..addRRect(
        RRect.fromRectAndRadius(bubbleRect, Radius.circular(radius)),
      );
    final tipPath = Path()
      ..moveTo(width / 2 - (compact ? 10 : 13) * scale, bubbleTop + bubbleHeight - 3 * scale)
      ..lineTo(width / 2, bubbleTop + bubbleHeight + tipHeight)
      ..lineTo(width / 2 + (compact ? 10 : 13) * scale, bubbleTop + bubbleHeight - 3 * scale)
      ..close();

    canvas.drawShadow(bubblePath, Colors.black.withValues(alpha: isSelected ? 0.26 : 0.18), isSelected ? 10 : 6, true);
    canvas.drawShadow(tipPath, Colors.black.withValues(alpha: 0.22), 4, true);

    final fillPaint = Paint()
      ..color = palette.background
      ..isAntiAlias = true;
    final borderPaint = Paint()
      ..color = palette.border
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..isAntiAlias = true;

    canvas.drawPath(tipPath, fillPaint);
    canvas.drawRRect(
      RRect.fromRectAndRadius(bubbleRect, Radius.circular(radius)),
      fillPaint,
    );
    canvas.drawPath(tipPath, borderPaint);
    canvas.drawRRect(
      RRect.fromRectAndRadius(bubbleRect, Radius.circular(radius)),
      borderPaint,
    );

    // White outer ring for selected state
    if (isSelected) {
      final ringPaint = Paint()
        ..color = Colors.white.withValues(alpha: 0.95)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..isAntiAlias = true;
      canvas.drawRRect(
        RRect.fromRectAndRadius(bubbleRect.inflate(2.5), Radius.circular(radius + 1.5)),
        ringPaint,
      );
    }

    _drawCenteredText(
      canvas: canvas,
      text: text,
      color: palette.foreground,
      maxWidth: bubbleWidth - (compact ? 12 : 16) * scale,
      center: Offset(width / 2, bubbleTop + bubbleHeight / 2 - 0.5),
      startFontSize: (compact ? 16 : 21) * scale,
      minFontSize: (compact ? 12 : 14) * scale,
    );

    final picture = recorder.endRecording();
    final image = await picture.toImage(width.toInt(), height.toInt());
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    return byteData!.buffer.asUint8List();
  }

  static Future<Uint8List> _drawClusterMarker({
    required int count,
  }) async {
    const width = 80.0;
    const height = 66.0;
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder, const Rect.fromLTWH(0, 0, width, height));

    final shadowPaint = Paint()
      ..color = Colors.black.withValues(alpha: 0.16)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
    canvas.drawCircle(const Offset(width / 2, 29), 24, shadowPaint);

    final outerPaint = Paint()
      ..color = Colors.white
      ..isAntiAlias = true;
    final ringPaint = Paint()
      ..color = const Color(0xFF0D9488)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..isAntiAlias = true;
    final tipPaint = Paint()
      ..color = const Color(0xFF0D9488)
      ..isAntiAlias = true;

    const bubbleRect = Rect.fromLTWH(12, 5, 56, 44);
    final bubbleRRect = RRect.fromRectAndRadius(
      bubbleRect,
      const Radius.circular(14),
    );
    canvas.drawRRect(bubbleRRect, outerPaint);
    canvas.drawRRect(bubbleRRect, ringPaint);

    _drawCenteredText(
      canvas: canvas,
      text: count > 999 ? '999+' : count.toString(),
      color: const Color(0xFF111827),
      maxWidth: 48,
      center: const Offset(width / 2, 23),
      startFontSize: 20,
      minFontSize: 13,
    );

    _drawCenteredText(
      canvas: canvas,
      text: 'istasyon',
      color: const Color(0xFF0D9488),
      maxWidth: 48,
      center: const Offset(width / 2, 38),
      startFontSize: 9,
      minFontSize: 7,
    );

    final tipPath = Path()
      ..moveTo(width / 2 - 6, 49)
      ..lineTo(width / 2, 60)
      ..lineTo(width / 2 + 6, 49)
      ..close();
    canvas.drawPath(tipPath, tipPaint);

    final picture = recorder.endRecording();
    final image = await picture.toImage(width.toInt(), height.toInt());
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    return byteData!.buffer.asUint8List();
  }

  static void _drawCenteredText({
    required Canvas canvas,
    required String text,
    required Color color,
    required double maxWidth,
    required Offset center,
    required double startFontSize,
    required double minFontSize,
  }) {
    var fontSize = startFontSize;
    late TextPainter painter;

    while (true) {
      painter = TextPainter(
        text: TextSpan(
          text: text,
          style: TextStyle(
            color: color,
            fontSize: fontSize,
            fontWeight: FontWeight.w900,
            height: 1,
          ),
        ),
        maxLines: 1,
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: maxWidth);

      if (painter.width <= maxWidth || fontSize <= minFontSize) break;
      fontSize -= 1;
    }

    painter.paint(
      canvas,
      Offset(center.dx - painter.width / 2, center.dy - painter.height / 2),
    );
  }
}

class _MarkerPalette {
  final Color background;
  final Color foreground;
  final Color border;

  const _MarkerPalette({
    required this.background,
    required this.foreground,
    required this.border,
  });

  /// Marker'ı geri çeker: marka rengi tanınmaya devam eder ama dikkat çekmez.
  /// Renkleri gri tonuna doğru harmanlar; opaklık düşürmek yerine harmanlamak
  /// gerekiyor çünkü marker haritanın üstüne PNG olarak basılıyor ve şeffaf
  /// piksel zeminle karışıp okunaksız hale geliyordu.
  _MarkerPalette dimmed() => _MarkerPalette(
        background: Color.lerp(background, const Color(0xFF9CA3AF), 0.55)!,
        foreground: Color.lerp(foreground, const Color(0xFF6B7280), 0.35)!,
        border: Color.lerp(border, const Color(0xFF9CA3AF), 0.55)!,
      );
}
