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
}
