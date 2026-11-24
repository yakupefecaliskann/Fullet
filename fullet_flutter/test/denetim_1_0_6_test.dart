// 24 Kasım 2026 denetiminde bulunan ve 1.0.6'da düzeltilen hataların
// regresyon kilitleri.
import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/models/station.dart';
import 'package:fullet_flutter/providers/user_preferences_provider.dart';
import 'package:fullet_flutter/services/notification_service.dart';
import 'package:fullet_flutter/services/price_alert_service.dart';
import 'package:timezone/data/latest.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

Station _station({
  required List<Map<String, dynamic>> prices,
  String brand = 'Shell',
  String visibility = 'visible',
}) {
  return Station.fromJson({
    'id': 'st-1',
    'marka': brand,
    'isim': brand,
    'il': 'ANKARA',
    'ilce': 'CANKAYA',
    'enlem': 39.9,
    'boylam': 32.8,
    'aktif': true,
    'visibility_status': visibility,
    'veri_kaynagi': 'find.shell.com/tr/fuel',
    'fiyatlar': prices,
  });
}

Map<String, dynamic> _price(String fuel, String status) => {
      'yakit_tipi': fuel,
      'fiyat': 69.40,
      'price_status': status,
    };

void main() {
  group('Shell konum istasyonu haritadan süzülmüyor', () {
    test('tüm fiyatları unknown olan görünür istasyon konum istasyonudur', () {
      final station = _station(prices: [
        _price('Kursunsuz 95', 'unknown'),
        _price('Motorin', 'unknown'),
      ]);
      expect(station.isLocationOnly, isTrue);
      // Hesap havuzuna GİRMEMELİ: fiyatı yok.
      expect(station.hasDisplayablePriceFor('Kursunsuz 95'), isFalse);
    });

    test('hiç fiyat satırı olmayan görünür istasyon da konum istasyonudur', () {
      expect(_station(prices: const []).isLocationOnly, isTrue);
    });

    test(
        'tek bir yakıtta bile gösterilebilir fiyatı olan konum istasyonu DEĞİL',
        () {
      // LPG satmayan fiyatlı bir istasyon LPG haritasında konum pini olarak
      // görünmemeli; bu ayrımı sağlayan kural bu.
      final station = _station(brand: 'Opet', prices: [
        _price('Kursunsuz 95', 'fresh'),
        _price('LPG', 'unknown'),
      ]);
      expect(station.isLocationOnly, isFalse);
    });

    test('gizli istasyon konum istasyonu sayılmaz', () {
      final station = _station(prices: const [], visibility: 'hidden');
      expect(station.isLocationOnly, isFalse);
    });
  });

  group('Fiyat alarmı yalnızca eşiğin ALTINDA tetiklenir', () {
    test(
        'eşiğe eşit fiyat tetiklemez (diyalog eşiği mevcut fiyatla dolduruyor)',
        () {
      expect(PriceAlertService.shouldTrigger(price: 69.40, threshold: 69.40),
          isFalse);
    });

    test('eşiğin altındaki fiyat tetikler', () {
      expect(PriceAlertService.shouldTrigger(price: 69.39, threshold: 69.40),
          isTrue);
    });

    test('fiyat bilinmiyorsa tetiklemez', () {
      expect(PriceAlertService.shouldTrigger(price: null, threshold: 69.40),
          isFalse);
    });
  });

  test('Şarj (Elektrik) artık seçilebilir yakıt değil', () {
    expect(UserPreferencesProvider.supportedFuels, isNot(contains('Elektrik')));
    expect(
      UserPreferencesProvider.supportedFuels,
      containsAll(['Kursunsuz 95', 'Motorin', 'LPG']),
    );
  });

  test('hatırlatıcı saat dilimi Türkiye saati (UTC+3), UTC değil', () {
    tz_data.initializeTimeZones();
    final location = tz.getLocation(appTimeZone);
    final noonUtc = DateTime.utc(2026, 11, 24, 6, 30);
    final local = tz.TZDateTime.from(noonUtc, location);
    expect(local.hour, 9);
    expect(local.minute, 30);
  });
}
