/// Türkçe metinleri arama/eşleştirme için tek bir kanonik biçime indirger.
///
/// Kritik ayrıntı: Dart'ta `'İ'.toLowerCase()` Unicode kuralı gereği
/// `'i' + U+0307` (birleşen nokta) üretir — tek karakter değil, İKİ karakter.
/// Bu yüzden `toLowerCase()`'ten SONRA yapılan `replaceAll('İ', 'i')` hiçbir
/// zaman eşleşmez; `İSMAİL PETROL` küçültüldüğünde içinde U+0307 kalır ve
/// kullanıcının yazdığı `"ismail"` bu dizede bulunmaz.
///
/// Çözüm iki katmanlı: `'İ'`yi küçültmeden ÖNCE çevir, ayrıca girdide zaten
/// bulunabilecek birleşen noktaları temizle.
const String combiningDotAbove = '\u0307';

String normalizeTurkish(String value) {
  return value
      .replaceAll('İ', 'i')
      .toLowerCase()
      .replaceAll(combiningDotAbove, '')
      .replaceAll('ı', 'i')
      .replaceAll('ğ', 'g')
      .replaceAll('ü', 'u')
      .replaceAll('ş', 's')
      .replaceAll('ö', 'o')
      .replaceAll('ç', 'c')
      .trim();
}
