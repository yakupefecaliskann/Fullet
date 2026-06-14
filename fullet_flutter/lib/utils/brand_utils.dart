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

String _normalizeBrandText(String value) {
  return value
      .toLowerCase()
      .trim()
      .replaceAll('ı', 'i')
      .replaceAll('İ', 'i')
      .replaceAll('ğ', 'g')
      .replaceAll('ü', 'u')
      .replaceAll('ş', 's')
      .replaceAll('ö', 'o')
      .replaceAll('ç', 'c');
}
