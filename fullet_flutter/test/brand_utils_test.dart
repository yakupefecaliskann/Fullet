import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/utils/brand_utils.dart';

void main() {
  test('canonicalBrandKey normalizes supported brand aliases', () {
    expect(canonicalBrandKey('Shell'), 'shell');
    expect(canonicalBrandKey('SHELL ISTANBUL'), 'shell');
    expect(canonicalBrandKey('Aytemiz'), 'aytemiz');
    expect(canonicalBrandKey('Petrol Ofisi'), 'petrol_ofisi');
    expect(canonicalBrandKey('PO'), 'petrol_ofisi');
    expect(canonicalBrandKey('BP'), 'bp');
    expect(canonicalBrandKey('Türkiye Petrolleri'), 'tp');
    expect(canonicalBrandKey('TP'), 'tp');
    expect(canonicalBrandKey('TPPD'), 'tp');
  });

  test('brand labels come from canonical keys', () {
    expect(brandLabelsForKeys({'shell', 'aytemiz'}), ['Shell', 'Aytemiz']);
    expect(brandDisplayLabelForKey('tp'), 'TP');
    expect(brandFilterSummary({'petrol_ofisi', 'bp'}), 'Petrol Ofisi, BP');
  });

  group('D-1: karanlik marka cipi bos harita dondurmuyor', () {
    // 14 Ekim 2026 denetimi: Shell kaynagi 9 Eylul'de olmus, 1309 istasyon
    // `hidden` olmus, ama filtre cipi listede ILK sirada durmaya devam edip
    // bos harita donduruyordu.
    const canli = {'opet', 'petrol_ofisi', 'bp', 'total', 'tp', 'aytemiz'};

    test('kullanilabilirlik BILINMIYOR ise hicbir cip kisitlanmaz', () {
      // Fail-open: null, "hicbir marka kullanilabilir degil" DEMEK DEGIL.
      for (final option in brandOptions) {
        expect(
          isBrandDataUnavailable(option.key, null),
          isFalse,
          reason: '${option.key} null kullanilabilirlikte kisitlanmamali',
        );
      }
      expect(unavailableBrandsAmong({'shell'}, null), isEmpty);
    });

    test('verisi olmayan marka karanlik, olanlar degil', () {
      expect(isBrandDataUnavailable('shell', canli), isTrue);
      for (final key in canli) {
        expect(isBrandDataUnavailable(key, canli), isFalse, reason: key);
      }
    });

    test('secili markalardan yalnizca karanlik olanlar donuyor', () {
      expect(unavailableBrandsAmong({'shell'}, canli), {'shell'});
      expect(unavailableBrandsAmong({'opet', 'bp'}, canli), isEmpty);
      // Kismi karanlik: kaydirma hala anlamli oldugu icin bos-durum metni
      // `every` ile karar veriyor, `any` ile degil.
      expect(unavailableBrandsAmong({'shell', 'opet'}, canli), {'shell'});
    });

    test('bos secim her zaman bos sonuc verir', () {
      expect(unavailableBrandsAmong(const {}, canli), isEmpty);
      expect(unavailableBrandsAmong(const {}, null), isEmpty);
    });

    test('kaynak dondugunde cip kendiliginde etkinlesir', () {
      // Hicbir yerde "shell" sabit kodlu istisna YOK: view onu saymaya
      // basladigi an cip yeniden calisir, kod degisikligi gerekmez.
      const shellDondu = {...canli, 'shell'};
      expect(isBrandDataUnavailable('shell', shellDondu), isFalse);
      expect(unavailableBrandsAmong({'shell'}, shellDondu), isEmpty);
    });
  });
}
