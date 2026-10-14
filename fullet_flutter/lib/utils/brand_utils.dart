import 'text_normalize.dart';

class BrandOption {
  final String key;
  final String label;
  final String displayLabel;

  const BrandOption({
    required this.key,
    required this.label,
    String? displayLabel,
  }) : displayLabel = displayLabel ?? label;
}

const brandOptions = <BrandOption>[
  BrandOption(key: 'shell', label: 'Shell'),
  BrandOption(key: 'opet', label: 'Opet'),
  BrandOption(key: 'petrol_ofisi', label: 'Petrol Ofisi'),
  BrandOption(key: 'bp', label: 'BP'),
  BrandOption(key: 'total', label: 'TotalEnergies'),
  BrandOption(
    key: 'tp',
    label: 'Türkiye Petrolleri',
    displayLabel: 'TP',
  ),
  BrandOption(key: 'aytemiz', label: 'Aytemiz'),
];

String canonicalBrandKey(String value) {
  final normalized = _normalizeBrandText(value);
  if (normalized.contains('shell')) return 'shell';
  if (normalized.contains('aytemiz')) return 'aytemiz';
  if (normalized.contains('opet')) return 'opet';
  if (normalized.contains('petrol') && normalized.contains('ofisi')) {
    return 'petrol_ofisi';
  }
  if (normalized == 'po') return 'petrol_ofisi';
  if (normalized == 'bp' ||
      normalized.startsWith('bp ') ||
      normalized.contains(' bp')) {
    return 'bp';
  }
  if (normalized.contains('total')) return 'total';
  if (normalized.contains('petrolleri') ||
      normalized.contains('petroleri') ||
      normalized == 'tp' ||
      normalized.contains('tppd')) {
    return 'tp';
  }
  return normalized;
}

String brandLabelForKey(String key) {
  for (final option in brandOptions) {
    if (option.key == key) return option.label;
  }
  return key;
}

String brandDisplayLabelForKey(String key) {
  for (final option in brandOptions) {
    if (option.key == key) return option.displayLabel;
  }
  return key;
}

List<String> brandLabelsForKeys(Set<String> keys) {
  return brandOptions
      .where((option) => keys.contains(option.key))
      .map((option) => option.label)
      .toList(growable: false);
}

String brandFilterSummary(Set<String> keys) {
  if (keys.isEmpty) return 'Tümü';
  return keys.map(brandDisplayLabelForKey).join(', ');
}

/// Bu markanın ŞU AN haritada gösterilecek verisi var mı yok mu.
///
/// [availableKeys] `null` ise cevap **BİLİNMİYOR** — sunucu sorgusu henüz
/// dönmemiş ya da başarısız olmuş olabilir — ve hiçbir çip kısıtlanmaz.
/// Boş küme ile karıştırılmamalı; `null` fail-open, boş küme "hiçbir markada
/// veri yok" demektir.
///
/// Hata maliyeti kasıtlı olarak asimetrik ele alınıyor: yanlış bir "veri yok"
/// etiketi ÇALIŞAN bir markayı kullanıcıdan saklar (gerçek zarar), eksik
/// etiket ise yalnızca denetim öncesi davranışa döner (tanıdık zarar).
bool isBrandDataUnavailable(String brandKey, Set<String>? availableKeys) {
  if (availableKeys == null) return false;
  return !availableKeys.contains(brandKey);
}

/// [selectedKeys] içinden şu anda verisi OLMAYAN markalar.
///
/// Boş-durum metni bununla karar veriyor: sonuç boşsa "bu bölgede yok"
/// (haritayı kaydırmak işe yarar), doluysa "kaynak şu anda yok"
/// (kaydırmak işe YARAMAZ ve kullanıcıya öyle söylemek yanlış olur).
Set<String> unavailableBrandsAmong(
  Set<String> selectedKeys,
  Set<String>? availableKeys,
) {
  if (availableKeys == null) return const <String>{};
  return selectedKeys
      .where((key) => !availableKeys.contains(key))
      .toSet();
}

// `replaceAll('İ', 'i')` burada `toLowerCase()`'ten SONRA geldiği için hiç
// eşleşmiyordu (bkz. text_normalize.dart). Tek ortak normalleştiriciye taşındı.
String _normalizeBrandText(String value) => normalizeTurkish(value);
