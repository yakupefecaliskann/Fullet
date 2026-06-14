import 'package:flutter_test/flutter_test.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:fullet_flutter/models/station.dart';
import 'package:fullet_flutter/services/smart_station_service.dart';

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
      'visibility_status': 'low_priority',
      'veri_kaynagi': 'api.opet.com.tr/api/fuelprices/allprices',
      'guncellenme_tarihi': '2026-05-07T07:30:00Z',
      'fiyatlar': [
        {
          'yakit_tipi': 'Kursunsuz 95',
          'fiyat': '63,50 TL',
          'price_status': 'fresh',
          'son_guncelleme': '2026-05-07T07:31:00Z',
        },
        {'yakit_tipi': 'Motorin', 'fiyat': '71.20', 'price_status': 'stale'},
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
    expect(station.visibilityStatus, 'low_priority');
    expect(station.isLowPriority, isTrue);
    expect(station.isVisibleInApp, isTrue);
    expect(station.priceTextFor('Kursunsuz 95'), '63.50');
    expect(station.priceTextFor('Motorin'), '71.20');
    expect(station.priceStatusFor('Motorin'), 'stale');
    expect(station.hasFreshPriceFor('Kursunsuz 95'), isTrue);
    expect(station.priceTextFor('LPG'), '-');
    expect(station.trendFor('Motorin'), -0.2);
    expect(station.dataSource, 'api.opet.com.tr/api/fuelprices/allprices');
    expect(station.hasOfficialRegionalSource, isTrue);
    expect(station.latestPriceUpdatedAt?.toUtc().toIso8601String(),
        '2026-05-07T07:31:00.000Z');
  });

  test('unknown prices are displayed as unavailable', () {
    final station = Station.fromJson({
      'id': 'station-unknown',
      'marka': 'Shell',
      'isim': 'Shell Test',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '40.99',
      'boylam': '29.03',
      'fiyatlar': [
        {
          'yakit_tipi': 'Kursunsuz 95',
          'fiyat': '63,50',
          'price_status': 'unknown',
        },
      ],
    });

    expect(station.priceStatusFor('Kursunsuz 95'), 'unknown');
    expect(station.priceValueFor('Kursunsuz 95'), isNull);
    expect(station.priceTextFor('Kursunsuz 95'), '-');
    expect(station.trustedPriceValueFor('Kursunsuz 95'), isNull);
  });

  test('stale prices can be shown but are excluded from smart calculations',
      () {
    final staleCheap = Station.fromJson({
      'id': 'stale-cheap',
      'marka': 'Opet',
      'isim': 'Opet Eski',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.00',
      'boylam': '29.00',
      'fiyatlar': [
        {
          'yakit_tipi': 'Kursunsuz 95',
          'fiyat': '10,00',
          'price_status': 'stale',
        },
      ],
    });
    final fresh = Station.fromJson({
      'id': 'fresh-real',
      'marka': 'Shell',
      'isim': 'Shell Güncel',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.01',
      'boylam': '29.01',
      'fiyatlar': [
        {
          'yakit_tipi': 'Kursunsuz 95',
          'fiyat': '65,00',
          'price_status': 'fresh',
        },
      ],
    });

    expect(staleCheap.priceValueFor('Kursunsuz 95'), 10);
    expect(staleCheap.trustedPriceValueFor('Kursunsuz 95'), isNull);

    final result = SmartStationService.calculateBestStations(
      location: const LatLng(41, 29),
      stations: [staleCheap, fresh],
      selectedFuel: 'Kursunsuz 95',
      tankCapacity: 50,
      fuelConsumption: 7,
    );

    expect(result.cheapestStationId, 'fresh-real');
    expect(result.mostLogicalStationId, 'fresh-real');
  });
}
