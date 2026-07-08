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

/// "Fiyata göre" sıralamada bayat/bilinmeyen bir fiyatın doğrulanmış bir
/// fiyattan "daha ucuz" görünüp yanlış yönlendirmesini önler — sıralama
/// önce bu rank'e, sonra fiyata göre yapılmalı (fresh her zaman önce).
int priceStatusRank(String? status) {
  switch (status) {
    case 'fresh':
      return 0;
    case 'stale':
      return 1;
    default:
      return 2;
  }
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
