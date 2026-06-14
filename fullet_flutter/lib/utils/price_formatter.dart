import 'package:flutter/material.dart';

String getLastPriceChangeText(Map<String, dynamic> station) {
  final history = station['fiyat_gecmisi'] as List<dynamic>?;
  if (history == null || history.isEmpty) return "Yeni";

  final sortedHistory = List<dynamic>.from(history)
    ..sort((a, b) {
      final aDate = DateTime.tryParse(a['degisim_tarihi']?.toString() ?? '');
      final bDate = DateTime.tryParse(b['degisim_tarihi']?.toString() ?? '');
      if (aDate == null && bDate == null) return 0;
      if (aDate == null) return 1;
      if (bDate == null) return -1;
      return bDate.compareTo(aDate);
    });
  final latest = sortedHistory.first;

  if (latest['degisim_tarihi'] == null) return "Yeni";

  final latestDate = DateTime.tryParse(latest['degisim_tarihi'].toString());
  if (latestDate == null) return "Yeni";

  final diffHours = DateTime.now().difference(latestDate).inHours;

  if (diffHours == 0) return "Güncel";
  if (diffHours < 24) return "${diffHours}s önce";
  return "${diffHours ~/ 24}g önce";
}

num? parseFuelPrice(dynamic rawValue) {
  if (rawValue == null) return null;
  if (rawValue is num && rawValue.isFinite) return rawValue;

  var value = rawValue.toString().trim();
  if (value.isEmpty || value == '-') return null;

  value = value.replaceAll(RegExp(r'[^0-9,.\-]'), '');
  if (value.isEmpty || value == '-') return null;

  final hasComma = value.contains(',');
  final hasDot = value.contains('.');
  if (hasComma && hasDot) {
    if (value.lastIndexOf(',') > value.lastIndexOf('.')) {
      value = value.replaceAll('.', '').replaceAll(',', '.');
    } else {
      value = value.replaceAll(',', '');
    }
  } else if (hasComma) {
    value = value.replaceAll(',', '.');
  }

  final parsed = num.tryParse(value);
  if (parsed == null || !parsed.isFinite) return null;
  return parsed;
}

String formatMarkerPrice(String priceText) {
  final price = parseFuelPrice(priceText);
  if (price == null) return 'Yok';
  return price.toStringAsFixed(2);
}

bool fuelMatches(dynamic sourceType, String targetType) {
  final source = sourceType?.toString().toLowerCase().trim() ?? '';
  final target = targetType.toLowerCase().trim();
  if (source.isEmpty) return false;
  if (source == target || source.contains(target) || target.contains(source)) {
    return true;
  }
  if (target == 'kursunsuz 95') {
    return source.contains('kursunsuz') || source.contains('benzin');
  }
  if (target == 'motorin') {
    return source.contains('motorin') || source.contains('dizel');
  }
  if (target == 'lpg') {
    return source.contains('lpg') || source.contains('otogaz');
  }
  if (target == 'elektrik') {
    return source.contains('elektrik') ||
        source.contains('sarj') ||
        source.contains('şarj') ||
        source.contains('kwh') ||
        source.contains('ev');
  }
  return false;
}

String getPrice(List<dynamic>? pricesArray, String targetType) {
  if (pricesArray == null) return '-';
  dynamic priceObj;
  for (var p in pricesArray) {
    if (p is! Map) continue;
    if (fuelMatches(p['yakit_tipi'], targetType)) {
      priceObj = p;
      break;
    }
  }
  if (priceObj != null) {
    final priceVal = parseFuelPrice(priceObj['fiyat']);
    if (priceVal != null) {
      return priceVal.toStringAsFixed(2);
    }
    return priceObj['fiyat']?.toString() ?? '-';
  }
  return '-';
}

Widget? getTrendIcon(Map<String, dynamic> station, String targetType) {
  final history = station['fiyat_gecmisi'] as List<dynamic>?;
  if (history == null || history.isEmpty) return null;

  final filteredHistory = history.where((h) {
    if (h is! Map) return false;
    return fuelMatches(h['yakit_tipi'], targetType);
  }).toList();

  if (filteredHistory.isNotEmpty) {
    filteredHistory.sort((a, b) {
      final aDate = DateTime.tryParse(a['degisim_tarihi']?.toString() ?? '');
      final bDate = DateTime.tryParse(b['degisim_tarihi']?.toString() ?? '');
      if (aDate == null && bDate == null) return 0;
      if (aDate == null) return 1;
      if (bDate == null) return -1;
      return bDate.compareTo(aDate);
    });
    final trendVal = parseFuelPrice(filteredHistory.first['fiyat_farki']);

    if (trendVal != null) {
      if (trendVal < 0) {
        return const Padding(
          padding: EdgeInsets.only(left: 4.0),
          child: Icon(Icons.arrow_downward, color: Color(0xFF16A34A), size: 16),
        );
      }
      if (trendVal > 0) {
        return const Padding(
          padding: EdgeInsets.only(left: 4.0),
          child: Icon(Icons.arrow_upward, color: Color(0xFFDC2626), size: 16),
        );
      }
    }
  }
  return null;
}
