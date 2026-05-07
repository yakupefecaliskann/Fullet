import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class MarkerIconFactory {
  MarkerIconFactory._();

  static final Map<String, BitmapDescriptor> _cache = {};

  static Future<BitmapDescriptor> stationPrice({
    required String brand,
    required String priceText,
    required bool hasPrice,
    required bool isCheapest,
    required bool isMostLogical,
    bool compact = false,
  }) async {
    final key =
        '$brand|$priceText|$hasPrice|$isCheapest|$isMostLogical|$compact';
    final cached = _cache[key];
    if (cached != null) return cached;

    final palette = _paletteFor(
      brand: brand,
      hasPrice: hasPrice,
      isCheapest: isCheapest,
      isMostLogical: isMostLogical,
    );

    final bytes = await _drawPriceMarker(
      text: priceText,
      palette: palette,
      compact: compact,
    );
    // google_maps_flutter_android 2.8.0 still expects the legacy descriptor
    // payload for runtime-generated marker PNGs.
    // ignore: deprecated_member_use
    final descriptor = BitmapDescriptor.fromBytes(bytes);
    _cache[key] = descriptor;
    return descriptor;
  }

  static Future<BitmapDescriptor> cluster({
    required int count,
  }) async {
    final key = 'cluster|$count';
    final cached = _cache[key];
    if (cached != null) return cached;

    final bytes = await _drawClusterMarker(count: count);
    // ignore: deprecated_member_use
    final descriptor = BitmapDescriptor.fromBytes(bytes);
    _cache[key] = descriptor;
    return descriptor;
  }

  static _MarkerPalette _paletteFor({
    required String brand,
    required bool hasPrice,
    required bool isCheapest,
    required bool isMostLogical,
  }) {
    if (!hasPrice) {
      return const _MarkerPalette(
        background: Color(0xFFF3F4F6),
        foreground: Color(0xFF6B7280),
        border: Color(0xFFFFFFFF),
      );
    }

    if (isMostLogical) {
      return const _MarkerPalette(
        background: Color(0xFF00A854),
        foreground: Colors.white,
        border: Color(0xFF064E3B),
      );
    }

    if (isCheapest) {
      return const _MarkerPalette(
        background: Color(0xFFEF4444),
        foreground: Colors.white,
        border: Color(0xFF7F1D1D),
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
      default:
        return const _MarkerPalette(
          background: Color(0xFF111827),
          foreground: Colors.white,
          border: Color(0xFFFFFFFF),
        );
    }
  }

  static Future<Uint8List> _drawPriceMarker({
    required String text,
    required _MarkerPalette palette,
    required bool compact,
  }) async {
    final width = compact ? 122.0 : 156.0;
    final height = compact ? 58.0 : 74.0;
    const bubbleLeft = 6.0;
    const bubbleTop = 6.0;
    final bubbleWidth = width - 12.0;
    final bubbleHeight = compact ? 34.0 : 44.0;
    final radius = compact ? 10.0 : 13.0;
    final tipHeight = compact ? 13.0 : 17.0;

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
      ..moveTo(width / 2 - (compact ? 10 : 13), bubbleTop + bubbleHeight - 3)
      ..lineTo(width / 2, bubbleTop + bubbleHeight + tipHeight)
      ..lineTo(width / 2 + (compact ? 10 : 13), bubbleTop + bubbleHeight - 3)
      ..close();

    canvas.drawShadow(bubblePath, Colors.black.withOpacity(0.30), 6, true);
    canvas.drawShadow(tipPath, Colors.black.withOpacity(0.22), 4, true);

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

    _drawCenteredText(
      canvas: canvas,
      text: text,
      color: palette.foreground,
      maxWidth: bubbleWidth - (compact ? 14 : 18),
      center: Offset(width / 2, bubbleTop + bubbleHeight / 2 - 0.5),
      startFontSize: compact ? 22 : 27,
      minFontSize: compact ? 15 : 18,
    );

    final picture = recorder.endRecording();
    final image = await picture.toImage(width.toInt(), height.toInt());
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    return byteData!.buffer.asUint8List();
  }

  static Future<Uint8List> _drawClusterMarker({
    required int count,
  }) async {
    const width = 96.0;
    const height = 78.0;
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder, const Rect.fromLTWH(0, 0, width, height));

    final shadowPaint = Paint()
      ..color = Colors.black.withOpacity(0.16)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
    canvas.drawCircle(const Offset(width / 2, 35), 29, shadowPaint);

    final outerPaint = Paint()
      ..color = Colors.white
      ..isAntiAlias = true;
    final ringPaint = Paint()
      ..color = const Color(0xFF10B981)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..isAntiAlias = true;
    final tipPaint = Paint()
      ..color = const Color(0xFF10B981)
      ..isAntiAlias = true;

    const bubbleRect = Rect.fromLTWH(16, 7, 64, 52);
    final bubbleRRect = RRect.fromRectAndRadius(
      bubbleRect,
      const Radius.circular(18),
    );
    canvas.drawRRect(bubbleRRect, outerPaint);
    canvas.drawRRect(bubbleRRect, ringPaint);

    _drawCenteredText(
      canvas: canvas,
      text: count > 999 ? '999+' : count.toString(),
      color: const Color(0xFF111827),
      maxWidth: 54,
      center: const Offset(width / 2, 27),
      startFontSize: 24,
      minFontSize: 15,
    );

    _drawCenteredText(
      canvas: canvas,
      text: 'istasyon',
      color: const Color(0xFF10B981),
      maxWidth: 56,
      center: const Offset(width / 2, 46),
      startFontSize: 10,
      minFontSize: 8,
    );

    final tipPath = Path()
      ..moveTo(width / 2 - 8, 58)
      ..lineTo(width / 2, 72)
      ..lineTo(width / 2 + 8, 58)
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
}
