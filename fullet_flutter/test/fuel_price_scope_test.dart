import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/models/fuel_price.dart';

/// F4 seffaflik katmani (4 Agustos 2026).
///
/// Olculdu: Ankara'daki 86 Shell istasyonu tek fiyat gosteriyor; veritabanindaki
/// 6.718 fiyat satirinin %100'u markanin IL GENELI ilan fiyati. Uygulama
/// bunu "bu istasyonun fiyati" gibi sunuyordu.
void main() {
  group('fiyat kapsami', () {
    test('sunucu kapsam gondermezse regional varsayilir', () {
      // Eksik veride "istasyondan dogrulandi" demek YANLIS yonde bir hatadir:
      // kullaniciya olmayan bir kesinlik vaat eder.
      final price = FuelPrice.fromJson({
        'yakit_tipi': 'Motorin',
        'fiyat': '82.16',
        'price_status': 'fresh',
      });

      expect(price.priceScope, 'regional');
      expect(price.isRegionalScope, isTrue);
    });

    test('station kapsami okunur', () {
      final price = FuelPrice.fromJson({
        'yakit_tipi': 'Motorin',
        'fiyat': '82.16',
        'fiyat_kapsami': 'station',
      });

      expect(price.isRegionalScope, isFalse);
    });

    test('taninmayan kapsam degeri regional sayilir', () {
      final price = FuelPrice.fromJson({
        'yakit_tipi': 'Motorin',
        'fiyat': '82.16',
        'fiyat_kapsami': 'saçmalık',
      });

      expect(price.priceScope, 'regional');
    });

    test('kapsam etiketi il adini kullanir', () {
      const price = FuelPrice(
        fuelType: 'Motorin',
        price: 82.16,
        priceScope: 'regional',
      );

      expect(price.scopeLabel(province: 'ANKARA'), 'ANKARA geneli ilan fiyatı');
      expect(price.scopeLabel(), 'Markanın il geneli ilan fiyatı');
    });

    test('istasyon kapsaminda il adi kullanilmaz', () {
      const price = FuelPrice(
        fuelType: 'Motorin',
        price: 82.16,
        priceScope: 'station',
      );

      expect(price.scopeLabel(province: 'ANKARA'), 'Bu istasyondan doğrulandı');
    });

    test('kapsam, fiyat durumundan bagimsizdir', () {
      // Bayat bir fiyat da il geneli olabilir; iki kavram karistirilmamali.
      final price = FuelPrice.fromJson({
        'yakit_tipi': 'Motorin',
        'fiyat': '82.16',
        'price_status': 'stale',
        'fiyat_kapsami': 'regional',
      });

      expect(price.isStale, isTrue);
      expect(price.isRegionalScope, isTrue);
      expect(price.isDisplayable, isTrue);
    });
  });
}
