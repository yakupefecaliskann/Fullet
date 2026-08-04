import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/models/station.dart';
import 'package:fullet_flutter/utils/station_search.dart';

/// Kullanicinin konumu (Kadikoy civari).
const double _userLat = 40.9900;
const double _userLng = 29.0300;

Station _station({
  required String id,
  String brand = 'Shell',
  String? name,
  double lat = 40.9900,
  double lng = 29.0300,
}) {
  return Station.fromJson({
    'id': id,
    'marka': brand,
    'isim': name ?? '$brand $id',
    'il': 'ISTANBUL',
    'ilce': 'KADIKOY',
    'enlem': lat.toString(),
    'boylam': lng.toString(),
  });
}

void main() {
  group('M1: arama sonuclari siralamadan SONRA kirpiliyor', () {
    test('en yakin istasyon, DB sirasinda 50 disinda olsa bile listeye giriyor',
        () {
      // Bug'in tam senaryosu: ayni markadan 200 kayit var ve kullaniciya EN
      // YAKIN olan, veritabani sirasinda en SONDA. Eski kod once ilk 50'yi
      // aliyor, sonra mesafeye gore siraliyordu -> bu istasyon hic gorunmuyordu.
      final stations = <Station>[
        // Uzaktakiler once (DB sirasi), her biri gittikce daha uzakta.
        for (var i = 0; i < 200; i++)
          _station(id: 'uzak-$i', lat: 41.5 + i * 0.01, lng: 29.5),
        // En yakin kayit listenin EN SONUNDA.
        _station(id: 'en-yakin', lat: _userLat, lng: _userLng),
      ];

      final results = rankStationSearchResults(
        stations: stations,
        query: 'Shell',
        selectedBrands: const {},
        favoriteStationIds: const {},
        recentStationIds: const [],
        latitude: _userLat,
        longitude: _userLng,
      );

      expect(results.length, kStationSearchResultLimit);
      expect(results.first.station.id, 'en-yakin',
          reason: 'Kirpma siralamadan once yapilirsa bu kayit listede olmaz');
    });

    test('sonuclar mesafeye gore artan sirada ve tavan asilmiyor', () {
      final stations = <Station>[
        for (var i = 0; i < 120; i++)
          _station(id: 'st-$i', lat: _userLat + (120 - i) * 0.01, lng: _userLng),
      ];

      final results = rankStationSearchResults(
        stations: stations,
        query: 'Shell',
        selectedBrands: const {},
        favoriteStationIds: const {},
        recentStationIds: const [],
        latitude: _userLat,
        longitude: _userLng,
      );

      expect(results.length, kStationSearchResultLimit);
      for (var i = 1; i < results.length; i++) {
        expect(results[i - 1].distanceKm! <= results[i].distanceKm!, isTrue,
            reason: 'Sonuclar mesafeye gore sirali olmali');
      }
      // En yakin 50 kayit st-119..st-70 olmali (i buyudukce mesafe kuculuyor).
      expect(results.first.station.id, 'st-119');
    });

    test('50 alti sonuc kirpilmiyor', () {
      final stations = <Station>[
        for (var i = 0; i < 10; i++)
          _station(id: 'st-$i', lat: _userLat + i * 0.01, lng: _userLng),
      ];

      final results = rankStationSearchResults(
        stations: stations,
        query: 'Shell',
        selectedBrands: const {},
        favoriteStationIds: const {},
        recentStationIds: const [],
        latitude: _userLat,
        longitude: _userLng,
      );

      expect(results.length, 10);
    });

    test('favori ve son bakilan, mesafe daha uzak olsa bile one geliyor', () {
      final stations = <Station>[
        _station(id: 'yakin', lat: _userLat, lng: _userLng),
        _station(id: 'favori', lat: _userLat + 0.5, lng: _userLng),
        _station(id: 'son-bakilan', lat: _userLat + 0.6, lng: _userLng),
      ];

      final results = rankStationSearchResults(
        stations: stations,
        query: 'Shell',
        selectedBrands: const {},
        favoriteStationIds: const {'favori'},
        recentStationIds: const ['son-bakilan'],
        latitude: _userLat,
        longitude: _userLng,
      );

      expect(results.map((r) => r.station.id).toList(),
          ['favori', 'son-bakilan', 'yakin']);
    });

    test('bos sorgu: yalnizca favori + son bakilan listeleniyor, kirpma yok',
        () {
      final stations = <Station>[
        for (var i = 0; i < 80; i++)
          _station(id: 'st-$i', lat: _userLat + i * 0.01, lng: _userLng),
      ];

      final results = rankStationSearchResults(
        stations: stations,
        query: '',
        selectedBrands: const {},
        favoriteStationIds: const {'st-5'},
        recentStationIds: const ['st-9'],
        latitude: _userLat,
        longitude: _userLng,
      );

      expect(results.map((r) => r.station.id).toList(), ['st-5', 'st-9']);
    });

    test('Turkce normalizasyon aramada calisiyor (buyuk I)', () {
      final stations = <Station>[
        _station(id: 'izmit', brand: 'Opet', name: 'İZMİT YOLU'),
        _station(id: 'diger', brand: 'Opet', name: 'KADIKOY'),
      ];

      final results = rankStationSearchResults(
        stations: stations,
        query: 'izmit',
        selectedBrands: const {},
        favoriteStationIds: const {},
        recentStationIds: const [],
        latitude: _userLat,
        longitude: _userLng,
      );

      expect(results.length, 1);
      expect(results.first.station.id, 'izmit');
    });

    test('M2: normalize edilmis arama metni istasyon basina BIR KEZ hesaplaniyor',
        () {
      // Eskiden her tus vurusunda ~6.000 istasyonun 4 alani birlestirilip
      // normalizeTurkish() cagriliyordu (tus basina ~42.000 string islemi,
      // UI thread'inde) ve siralama karsilastiricisi ayni stringleri
      // O(n log n) kez yeniden normalize ediyordu. Deger artik saklaniyor:
      // ayni String ORNEGI donmeli, esdeger bir kopya degil.
      final station = _station(id: 'st-1', brand: 'Opet', name: 'İZMİT YOLU');

      expect(identical(station.searchHaystack, station.searchHaystack), isTrue);
      expect(identical(station.normalizedBrand, station.normalizedBrand), isTrue);
      expect(
          identical(
              station.normalizedDisplayName, station.normalizedDisplayName),
          isTrue);

      // Icerik dogru olmali: dort alan da aranabilir kalmali.
      expect(station.searchHaystack.contains('izmit'), isTrue);
      expect(station.searchHaystack.contains('opet'), isTrue);
      expect(station.searchHaystack.contains('istanbul'), isTrue);
      expect(station.searchHaystack.contains('kadikoy'), isTrue);
    });

    test('marka filtresi aramayi suzuyor', () {
      final stations = <Station>[
        _station(id: 'shell-1', brand: 'Shell'),
        _station(id: 'opet-1', brand: 'Opet'),
      ];

      final results = rankStationSearchResults(
        stations: stations,
        query: 'ISTANBUL',
        selectedBrands: const {'opet'},
        favoriteStationIds: const {},
        recentStationIds: const [],
        latitude: _userLat,
        longitude: _userLng,
      );

      expect(results.map((r) => r.station.id).toList(), ['opet-1']);
    });
  });
}
