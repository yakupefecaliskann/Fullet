import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/models/station.dart';

void main() {
  test('Station parses nested Supabase fuel prices safely', () {
    final station = Station.fromJson({
      'id': 'station-1',
      'marka': 'Opet',
      'isim': 'Opet Test',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '40.99',
      'boylam': '29.03',
      'veri_kaynagi': 'api.opet.com.tr/api/fuelprices/allprices',
      'guncellenme_tarihi': '2026-05-07T07:30:00Z',
      'fiyatlar': [
        {
          'yakit_tipi': 'Kursunsuz 95',
          'fiyat': '63,50 TL',
          'son_guncelleme': '2026-05-07T07:31:00Z',
        },
        {'yakit_tipi': 'Motorin', 'fiyat': '71.20'},
        {'yakit_tipi': 'LPG', 'fiyat': '-'},
      ],
      'fiyat_gecmisi': [
        {
          'yakit_tipi': 'Motorin',
          'fiyat_farki': '-0,20',
          'degisim_tarihi': DateTime.now().toIso8601String(),
        },
      ],
    });

    expect(station.hasLocation, isTrue);
    expect(station.priceTextFor('Kursunsuz 95'), '63.50');
    expect(station.priceTextFor('Motorin'), '71.20');
    expect(station.priceTextFor('LPG'), '-');
    expect(station.trendFor('Motorin'), -0.2);
    expect(station.dataSource, 'api.opet.com.tr/api/fuelprices/allprices');
    expect(station.hasOfficialRegionalSource, isTrue);
    expect(station.latestPriceUpdatedAt?.toUtc().toIso8601String(),
        '2026-05-07T07:31:00.000Z');
  });
}
