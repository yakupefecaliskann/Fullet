import '../models/station.dart';
import 'brand_utils.dart';
import 'distance_calculator.dart';
import 'price_formatter.dart';
import 'text_normalize.dart';

/// Arama sonuç listesinde gösterilen en fazla kayıt sayısı.
const int kStationSearchResultLimit = 50;

/// Arama sonucu tek satırı. Eskiden `modern_map_screen.dart` içinde private bir
/// sınıftı; M1 düzeltmesinin regresyon testi yazılabilsin diye buraya taşındı.
class StationSearchResult {
  final Station station;
  final double? distanceKm;
  final bool isFavorite;
  final int recentIndex;

  const StationSearchResult({
    required this.station,
    required this.distanceKm,
    required this.isFavorite,
    required this.recentIndex,
  });

  bool get isRecent => recentIndex >= 0;
}

/// Favori → son bakılan → diğer.
int stationSearchPinRank(StationSearchResult result) {
  if (result.isFavorite) return 0;
  if (result.isRecent) return 1;
  return 2;
}

/// Metin aramasının sonuçlarını süzer, mesafeye göre sıralar ve **en sonda**
/// kırpar.
///
/// **M1 (düzeltildi):** Kırpma eskiden süzmeden hemen sonra, yani mesafe daha
/// hesaplanmadan yapılıyordu. `filtered` o noktada önbelleğin döndürdüğü
/// veritabanı sırasındaydı; "Shell" araması ülke genelindeki ilk 50 Shell
/// kaydını alıp SONRA mesafeye göre sıralıyordu. Kullanıcının 2 km ötesindeki
/// Shell o ilk 50'ye girmediyse sonuçlarda **hiç görünmüyordu** — üstelik liste
/// "en yakın" gibi sıralanmış göründüğü için eksiklik fark edilmiyordu. Binlerce
/// kaydı olan markalarda (Shell, Opet, Petrol Ofisi) sistematik tetikleniyordu.
///
/// Sıralama ölçütleri, sırasıyla:
/// 1. Sorgu ile başlayanlar (marka veya istasyon adı) öne,
/// 2. Favori → son bakılan → diğer,
/// 3. Boş sorguda son bakılma sırası,
/// 4. Mesafe (yakın önce).
List<StationSearchResult> rankStationSearchResults({
  required List<Station> stations,
  required String query,
  required Set<String> selectedBrands,
  required Set<String> favoriteStationIds,
  required List<String> recentStationIds,
  required double latitude,
  required double longitude,
  int limit = kStationSearchResultLimit,
}) {
  final normalizedQuery = normalizeTurkish(query);

  var filtered = stations.where((station) {
    if (selectedBrands.isNotEmpty &&
        !selectedBrands.contains(canonicalBrandKey(station.brand))) {
      return false;
    }
    if (!station.isVisibleInApp) return false;
    if (normalizedQuery.isEmpty) return true;
    // M2: istasyon başına bir kez hesaplanıp saklanan normalize metin.
    return station.searchHaystack.contains(normalizedQuery);
  }).toList();

  // Sorgu boşken liste "hızlı erişim" listesidir: yalnızca favoriler ve son
  // bakılanlar. Bu bir kırpma değil, farklı bir görünüm.
  if (normalizedQuery.isEmpty) {
    filtered = filtered
        .where((s) =>
            favoriteStationIds.contains(s.id) || recentStationIds.contains(s.id))
        .toList();
  }

  final results = filtered.map((station) {
    return StationSearchResult(
      station: station,
      distanceKm: getDistanceKm(
        latitude,
        longitude,
        station.latitude,
        station.longitude,
      ),
      isFavorite: favoriteStationIds.contains(station.id),
      recentIndex: recentStationIds.indexOf(station.id),
    );
  }).toList();

  results.sort((a, b) {
    if (normalizedQuery.isNotEmpty) {
      // M2: karşılaştırıcı her çağrıldığında yeniden normalize etmiyor.
      final aStarts =
          a.station.normalizedDisplayName.startsWith(normalizedQuery) ||
              a.station.normalizedBrand.startsWith(normalizedQuery);
      final bStarts =
          b.station.normalizedDisplayName.startsWith(normalizedQuery) ||
              b.station.normalizedBrand.startsWith(normalizedQuery);
      if (aStarts != bStarts) return aStarts ? -1 : 1;
    }
    final pinCompare =
        stationSearchPinRank(a).compareTo(stationSearchPinRank(b));
    if (pinCompare != 0) return pinCompare;
    if (normalizedQuery.isEmpty && a.isRecent && b.isRecent) {
      final recentCompare = a.recentIndex.compareTo(b.recentIndex);
      if (recentCompare != 0) return recentCompare;
    }
    return (a.distanceKm ?? double.maxFinite)
        .compareTo(b.distanceKm ?? double.maxFinite);
  });

  // M1: kırpma SIRALAMADAN SONRA. Gösterilen 50 kayıt artık eşleşenlerin
  // gerçekten en alakalı/en yakın 50'si.
  if (normalizedQuery.isNotEmpty && results.length > limit) {
    return results.sublist(0, limit);
  }
  return results;
}

/// Fiyata göre sıralanmış liste — `(price_status_rank, fiyat)` ile sıralar.
/// Bayat/bilinmeyen bir fiyat doğrulanmış bir fiyattan asla "daha ucuz"
/// görünmez (fresh her zaman önce), aksi halde ürünün "yanlış fiyat
/// göstermeme" ilkesi ihlal edilir. Bu liste kırpılmaz.
List<StationSearchResult> rankStationsByPrice({
  required List<Station> stations,
  required String selectedFuel,
  required Set<String> selectedBrands,
  required Set<String> favoriteStationIds,
  required List<String> recentStationIds,
  required double latitude,
  required double longitude,
}) {
  final filtered = stations.where((station) {
    if (selectedBrands.isNotEmpty &&
        !selectedBrands.contains(canonicalBrandKey(station.brand))) {
      return false;
    }
    if (!station.isVisibleInApp) return false;
    return station.hasDisplayablePriceFor(selectedFuel);
  }).toList();

  final results = filtered.map((station) {
    return StationSearchResult(
      station: station,
      distanceKm: getDistanceKm(
        latitude,
        longitude,
        station.latitude,
        station.longitude,
      ),
      isFavorite: favoriteStationIds.contains(station.id),
      recentIndex: recentStationIds.indexOf(station.id),
    );
  }).toList();

  results.sort((a, b) {
    final rankCompare = priceStatusRank(a.station.priceStatusFor(selectedFuel))
        .compareTo(priceStatusRank(b.station.priceStatusFor(selectedFuel)));
    if (rankCompare != 0) return rankCompare;
    final aPrice = a.station.priceValueFor(selectedFuel) ?? double.maxFinite;
    final bPrice = b.station.priceValueFor(selectedFuel) ?? double.maxFinite;
    return aPrice.compareTo(bPrice);
  });

  return results;
}
