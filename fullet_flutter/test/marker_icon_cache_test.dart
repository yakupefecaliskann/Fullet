import 'package:flutter_test/flutter_test.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:fullet_flutter/utils/marker_icon_factory.dart';

/// H1 regresyon kilidi: marker ikon onbellegi eskiden sinirsizdi ve hicbir
/// yerde temizlenmiyordu. Anahtar fiyat metnini ve durum bayraklarini
/// icerdigi icin oturum boyunca surekli yeni girisler uretiliyordu; surus
/// modunda (her konum guncellemesinde tam marker yeniden insasi) onbellek
/// monoton buyuyordu. Asagidaki testler tavani ve LRU tahliyesini kilitler.
void main() {
  setUp(MarkerIconFactory.resetCacheForTest);

  test('onbellek tavani asilmiyor', () {
    final limit = MarkerIconFactory.maxCacheEntries;

    for (var i = 0; i < limit * 2; i++) {
      MarkerIconFactory.putForTest('key-$i', BitmapDescriptor.defaultMarker);
    }

    expect(MarkerIconFactory.cacheLength, limit);
  });

  test('tavan asilinca EN ESKI giris tahliye ediliyor', () {
    final limit = MarkerIconFactory.maxCacheEntries;

    for (var i = 0; i < limit; i++) {
      MarkerIconFactory.putForTest('key-$i', BitmapDescriptor.defaultMarker);
    }
    // Tavan doldu; bir tane daha eklenince ilk giris dusmeli.
    MarkerIconFactory.putForTest('tasiran', BitmapDescriptor.defaultMarker);

    expect(MarkerIconFactory.cacheLength, limit);
    expect(MarkerIconFactory.getForTest('key-0'), isNull);
    expect(MarkerIconFactory.getForTest('key-1'), isNotNull);
    expect(MarkerIconFactory.getForTest('tasiran'), isNotNull);
  });

  test('erisilen giris LRU sirasinda yenileniyor (tahliyeden korunuyor)', () {
    final limit = MarkerIconFactory.maxCacheEntries;

    for (var i = 0; i < limit; i++) {
      MarkerIconFactory.putForTest('key-$i', BitmapDescriptor.defaultMarker);
    }

    // key-0 en eski giris; okumak onu "en yeni" konuma tasimali.
    expect(MarkerIconFactory.getForTest('key-0'), isNotNull);

    MarkerIconFactory.putForTest('tasiran', BitmapDescriptor.defaultMarker);

    expect(MarkerIconFactory.cacheLength, limit);
    expect(MarkerIconFactory.getForTest('key-0'), isNotNull,
        reason: 'Erisilen giris tahliye edilmemeli (LRU)');
    expect(MarkerIconFactory.getForTest('key-1'), isNull,
        reason: 'Artik en eski giris key-1 olmali');
  });

  test('ayni anahtarin tekrar yazilmasi onbellegi sisirmiyor', () {
    for (var i = 0; i < 100; i++) {
      MarkerIconFactory.putForTest('sabit', BitmapDescriptor.defaultMarker);
    }

    expect(MarkerIconFactory.cacheLength, 1);
  });
}
