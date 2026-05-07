import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/utils/price_formatter.dart';

void main() {
  group('parseFuelPrice', () {
    test('parses decimal values written with dot or comma', () {
      expect(parseFuelPrice('45.78'), 45.78);
      expect(parseFuelPrice('45,78'), 45.78);
    });

    test('parses formatted Turkish price text', () {
      expect(parseFuelPrice('1.245,90 TL'), 1245.90);
      expect(parseFuelPrice('1,245.90'), 1245.90);
    });

    test('returns null for missing values', () {
      expect(parseFuelPrice(null), isNull);
      expect(parseFuelPrice('-'), isNull);
      expect(parseFuelPrice(''), isNull);
    });
  });

  group('getPrice', () {
    final prices = [
      {'yakit_tipi': 'Kursunsuz 95', 'fiyat': '45,78'},
      {'yakit_tipi': 'Motorin', 'fiyat': 43.2},
      {'yakit_tipi': 'Otogaz LPG', 'fiyat': '22.10 TL'},
    ];

    test('normalizes matching fuel prices', () {
      expect(getPrice(prices, 'Kursunsuz 95'), '45.78');
      expect(getPrice(prices, 'Motorin'), '43.20');
      expect(getPrice(prices, 'LPG'), '22.10');
    });

    test('returns dash when no matching fuel exists', () {
      expect(getPrice(prices, 'Elektrik'), '-');
    });
  });

  test('formatMarkerPrice never returns clipped currency-only text', () {
    expect(formatMarkerPrice('45,78 TL'), '45.78');
    expect(formatMarkerPrice('-'), 'Yok');
  });
}
