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

  test('S2-3: latestPriceUpdatedAt istasyon satirinin zamanini kullanmaz', () {
    // guncellenme_tarihi fiyattan cok daha yeni; eskiden bu deger sizip
    // uc haftalik fiyati "Guncel" gosteriyordu.
    final station = Station.fromJson({
      'id': 'stale-station-row-fresh',
      'marka': 'Shell',
      'isim': 'Shell Test',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.00',
      'boylam': '29.00',
      'guncellenme_tarihi': DateTime.now().toUtc().toIso8601String(),
      'fiyatlar': [
        {
          'yakit_tipi': 'Motorin',
          'fiyat': '71,20',
          'price_status': 'stale',
          'son_guncelleme': '2026-05-07T07:31:00Z',
        },
      ],
    });

    expect(station.latestPriceUpdatedAt?.toUtc().toIso8601String(),
        '2026-05-07T07:31:00.000Z');
    expect(station.getLastPriceChangeText('Motorin'), isNot('Güncel'));
  });

  test('S2-3: getLastPriceChangeText yakit tipine duyarli', () {
    // Motorin az once degisti, LPG uc hafta once. LPG karti "Guncel" dememeli.
    final station = Station.fromJson({
      'id': 'per-fuel-history',
      'marka': 'Opet',
      'isim': 'Opet Test',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.00',
      'boylam': '29.00',
      'fiyatlar': [
        {'yakit_tipi': 'Motorin', 'fiyat': '71,20', 'price_status': 'fresh'},
        {'yakit_tipi': 'LPG', 'fiyat': '32,10', 'price_status': 'stale'},
      ],
      'fiyat_gecmisi': [
        {
          'yakit_tipi': 'Motorin',
          'fiyat_farki': '-0,20',
          'degisim_tarihi': DateTime.now().toIso8601String(),
        },
        {
          'yakit_tipi': 'LPG',
          'fiyat_farki': '0,15',
          'degisim_tarihi': DateTime.now()
              .subtract(const Duration(days: 21))
              .toIso8601String(),
        },
      ],
    });

    expect(station.getLastPriceChangeText('Motorin'), 'Güncel');
    expect(station.getLastPriceChangeText('LPG'), '21 gün önce');
  });

  test('S2-2: bayat fiyat harita havuzuyla ayni hesaba girer', () {
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
    // Bayat fiyat hala "guvenilir" degil — ama artik harita hesabini
    // belirleyen olcut bu degil.
    expect(staleCheap.trustedPriceValueFor('Kursunsuz 95'), isNull);

    final result = SmartStationService.calculateBestStations(
      location: const LatLng(41, 29),
      stations: [staleCheap, fresh],
      selectedFuel: 'Kursunsuz 95',
      tankCapacity: 50,
      fuelConsumption: 7,
    );

    // POLITIKA DEGISIKLIGI (S2-2): marker 10,00 gosterirken tacin 65,00'teki
    // baska istasyonda durmasi kabul edilemezdi. Tek havuz: gosterilen fiyat
    // hesaba da girer.
    expect(result.cheapestStationId, 'stale-cheap');
    expect(result.mostLogicalStationId, 'stale-cheap');
  });

  test('S2-2: fiyat esitse taze olan taci alir', () {
    Station build(String id, String status) => Station.fromJson({
          'id': id,
          'marka': 'Opet',
          'isim': id,
          'il': 'ISTANBUL',
          'ilce': 'KADIKOY',
          'enlem': '41.00',
          'boylam': '29.00',
          'fiyatlar': [
            {
              'yakit_tipi': 'Kursunsuz 95',
              'fiyat': '65,00',
              'price_status': status,
            },
          ],
        });

    final result = SmartStationService.calculateBestStations(
      location: const LatLng(41, 29),
      stations: [build('bayat', 'stale'), build('taze', 'fresh')],
      selectedFuel: 'Kursunsuz 95',
      tankCapacity: 50,
      fuelConsumption: 7,
    );

    expect(result.cheapestStationId, 'taze');
  });

  test('S2-2: unknown fiyat hicbir havuza girmez', () {
    final unknown = Station.fromJson({
      'id': 'unknown-cheap',
      'marka': 'Shell',
      'isim': 'Shell Bilinmiyor',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.00',
      'boylam': '29.00',
      'fiyatlar': [
        {'yakit_tipi': 'Kursunsuz 95', 'fiyat': '1,00', 'price_status': 'unknown'},
      ],
    });
    final fresh = Station.fromJson({
      'id': 'fresh-real',
      'marka': 'Opet',
      'isim': 'Opet Guncel',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.01',
      'boylam': '29.01',
      'fiyatlar': [
        {'yakit_tipi': 'Kursunsuz 95', 'fiyat': '65,00', 'price_status': 'fresh'},
      ],
    });

    final result = SmartStationService.calculateBestStations(
      location: const LatLng(41, 29),
      stations: [unknown, fresh],
      selectedFuel: 'Kursunsuz 95',
      tankCapacity: 50,
      fuelConsumption: 7,
    );

    expect(result.cheapestStationId, 'fresh-real');
  });

  test('S2-1: yakit filtresi gercekten suzuyor', () {
    // `_stationsWithFuel` icindeki kosulun ta kendisi. Eskiden `||` oldugu ve
    // liste zaten isVisibleInApp suzgecinden gectigi icin her istasyon geciyordu.
    final withLpg = Station.fromJson({
      'id': 'lpg-var',
      'marka': 'Opet',
      'isim': 'Opet LPG',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.00',
      'boylam': '29.00',
      'visibility_status': 'visible',
      'fiyatlar': [
        {'yakit_tipi': 'LPG', 'fiyat': '32,10', 'price_status': 'fresh'},
      ],
    });
    final withoutLpg = Station.fromJson({
      'id': 'lpg-yok',
      'marka': 'Shell',
      'isim': 'Shell Motorin',
      'il': 'ISTANBUL',
      'ilce': 'KADIKOY',
      'enlem': '41.01',
      'boylam': '29.01',
      'visibility_status': 'visible',
      'fiyatlar': [
        {'yakit_tipi': 'Motorin', 'fiyat': '71,20', 'price_status': 'fresh'},
      ],
    });

    final stations = [withLpg, withoutLpg];
    final lpgOnly = stations
        .where((s) => s.hasDisplayablePriceFor('LPG') && s.isVisibleInApp)
        .map((s) => s.id)
        .toList();

    expect(lpgOnly, ['lpg-var']);
    expect(withoutLpg.isVisibleInApp, isTrue,
        reason: 'gorunur ama LPG satmiyor — filtre yine de elemeli');
  });

  test('Madde 21: low_priority istasyon tac alamaz', () {
    // `low_priority` = "7 gundur hicbir bot bu kaydi dogrulamadi"
    // (pg_cron JOB 3). Konumu veya varligi supheli; kullaniciyi oraya
    // yonlendirmek en ucuzu bulmak degil, yanlis yere gondermektir.
    // Bu mekanizma kuruluydu ama HICBIR YERE BAGLI DEGILDI: uygulama
    // low_priority'yi normal `visible` gibi gosteriyordu (yol haritasi
    // madde 21 / S3-3). Canlida 989 istasyon bu durumdaydi.
    Station build(String id, String visibility, String price) =>
        Station.fromJson({
          'id': id,
          'marka': 'Opet',
          'isim': 'Opet $id',
          'il': 'ISTANBUL',
          'ilce': 'KADIKOY',
          'enlem': '41.00',
          'boylam': '29.00',
          'visibility_status': visibility,
          'fiyatlar': [
            {
              'yakit_tipi': 'Kursunsuz 95',
              'fiyat': price,
              'price_status': 'fresh',
            },
          ],
        });

    final ucuzAmaSupheli = build('supheli', 'low_priority', '60,00');
    final pahaliAmaSaglam = build('saglam', 'visible', '65,00');

    final result = SmartStationService.calculateBestStations(
      location: const LatLng(41, 29),
      stations: [ucuzAmaSupheli, pahaliAmaSaglam],
      selectedFuel: 'Kursunsuz 95',
      tankCapacity: 50,
      fuelConsumption: 7,
    );

    expect(result.cheapestStationId, 'saglam',
        reason: 'daha ucuz olsa bile low_priority tac alamaz');
    expect(result.mostLogicalStationId, 'saglam');
    // Haritadan SILINMEZ — fiyati hala dogru olabilir, sadece soluk gosterilir
    // ve tavsiye edilmez.
    expect(ucuzAmaSupheli.isVisibleInApp, isTrue);
    expect(ucuzAmaSupheli.isLowPriority, isTrue);
  });
}
