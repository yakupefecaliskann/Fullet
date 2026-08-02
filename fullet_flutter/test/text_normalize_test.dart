import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/utils/brand_utils.dart';
import 'package:fullet_flutter/utils/text_normalize.dart';

void main() {
  test('S2-4 NOTU: Dart U+0130 icin BASIT esleme yapiyor', () {
    // Yol haritasindaki S2-4 bulgusu "Dart'ta 'İ'.toLowerCase() 'i'+U+0307
    // uretir" diyordu. Dart 3.12.2'de bu DOGRU DEGIL: U+0130 dogrudan U+0069'a
    // duser, tek karakter. Yani eski `_normalize` de calisiyordu; S2-4
    // kullanici tarafinda bir hata degildi.
    //
    // Bu testi tutuyoruz cunku Dart tam Unicode eslemesine gecerse (SpecialCasing
    // kurali) davranis sessizce degisir ve arama kirilir. O gun bu test dusecek
    // ve normalizeTurkish'teki U+0307 temizligi yuk tasimaya baslayacak.
    expect('İ'.toLowerCase(), 'i');
    expect('İ'.toLowerCase().codeUnits, [0x69]);
  });

  test('S2-4: buyuk I ile yazilan isimler aranabiliyor', () {
    final haystack = normalizeTurkish('İSMAİL PETROL');
    expect(haystack, 'ismail petrol');
    expect(haystack.contains(normalizeTurkish('ismail')), isTrue);
    expect(haystack.contains(normalizeTurkish('İsmail')), isTrue);
    expect(haystack.startsWith(normalizeTurkish('İSM')), isTrue);
  });

  test('S2-4: girdide zaten bulunan birlesen nokta temizleniyor', () {
    expect(normalizeTurkish('i${combiningDotAbove}smail'), 'ismail');
  });

  test('S2-4: diger Turkce harfler korunuyor', () {
    expect(normalizeTurkish('ÇAĞLAYAN Şişli Öğüt ÜNLÜ'), 'caglayan sisli ogut unlu');
    expect(normalizeTurkish('  Kadıköy  '), 'kadikoy');
  });

  test('S2-4: marka normalizasyonu da ayni yoldan geciyor', () {
    // canonicalBrandKey icindeki _normalizeBrandText de `toLowerCase`'ten
    // sonra 'İ' degistirmeye calisiyordu — hicbir zaman eslesmiyordu.
    expect(canonicalBrandKey('TÜRKİYE PETROLLERİ'), 'tp');
    expect(canonicalBrandKey('Türkiye Petrolleri'), 'tp');
    expect(canonicalBrandKey('PETROL OFİSİ'), 'petrol_ofisi');
    expect(canonicalBrandKey('Petrol Ofisi'), 'petrol_ofisi');
  });
}
