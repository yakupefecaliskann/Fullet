import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/news_item.dart';
import '../models/station.dart';
import '../utils/distance_calculator.dart';

class SupabaseService {
  static final SupabaseClient client = Supabase.instance.client;
  static List<Station>? _allStationsCache;
  static DateTime? _allStationsCacheTime;
  static Future<List<Station>>? _allStationsInFlight;
  static String? lastStationFetchError;
  static String? lastAllStationsFetchError;
  static const _allStationsCacheDuration = Duration(minutes: 5);

  static const _stationSelect = '''
    id,
    marka,
    isim,
    il,
    ilce,
    enlem,
    boylam,
    veri_kaynagi,
    guncellenme_tarihi,
    fiyatlar (yakit_tipi, fiyat, son_guncelleme),
    fiyat_gecmisi (yakit_tipi, fiyat_farki, degisim_tarihi)
  ''';

  static const _stationListSelect = '''
    id,
    marka,
    isim,
    il,
    ilce,
    enlem,
    boylam,
    veri_kaynagi,
    guncellenme_tarihi,
    fiyatlar (yakit_tipi, fiyat, son_guncelleme)
  ''';

  static Future<List<Station>> fetchStations({
    required double latitude,
    required double longitude,
    double maxDistMeters = 20000,
    int maxResults = 250,
  }) async {
    try {
      final response = await client.rpc('get_nearby_stations', params: {
        'lat': latitude,
        'lng': longitude,
        'max_dist_meters': maxDistMeters.toInt(),
        'max_results': maxResults,
      }).select(_stationSelect);

      lastStationFetchError = null;
      return _parseStations(response);
    } catch (e) {
      debugPrint('Supabase station fetch with max_results failed: $e');
      return _fetchStationsLegacy(
        latitude: latitude,
        longitude: longitude,
        maxDistMeters: maxDistMeters,
        maxResults: maxResults,
      );
    }
  }

  static Future<List<Station>> _fetchStationsLegacy({
    required double latitude,
    required double longitude,
    required double maxDistMeters,
    required int maxResults,
  }) async {
    try {
      final response = await client.rpc('get_nearby_stations', params: {
        'lat': latitude,
        'lng': longitude,
        'max_dist_meters': maxDistMeters.toInt(),
      }).select(_stationSelect);

      final stations = _parseStations(response);
      if (stations.length >= 50 && maxResults > stations.length) {
        return _fetchStationsFromTableFallback(
          latitude: latitude,
          longitude: longitude,
          maxDistMeters: maxDistMeters,
          maxResults: maxResults,
        );
      }
      lastStationFetchError = null;
      return stations;
    } catch (e) {
      debugPrint('Supabase station fetch failed: $e');
      lastStationFetchError = 'İstasyon verisi alınamadı.';
      return [];
    }
  }

  static Future<List<Station>> _fetchStationsFromTableFallback({
    required double latitude,
    required double longitude,
    required double maxDistMeters,
    required int maxResults,
  }) async {
    try {
      final allStations = await _fetchAllStationsCached();
      final maxKm = maxDistMeters / 1000;
      final withDistance = allStations
          .map((station) {
            final distance = getDistanceKm(
              latitude,
              longitude,
              station.latitude,
              station.longitude,
            );
            return _StationDistance(station, distance);
          })
          .where((item) => item.distanceKm != null && item.distanceKm! <= maxKm)
          .toList()
        ..sort((a, b) => a.distanceKm!.compareTo(b.distanceKm!));

      return withDistance
          .take(maxResults)
          .map((item) => item.station)
          .toList(growable: false);
    } catch (e) {
      debugPrint('Station table fallback failed: $e');
      lastStationFetchError = 'İstasyon verisi alınamadı.';
      return [];
    }
  }

  static Future<List<Station>> _fetchAllStationsCached() async {
    final now = DateTime.now();
    final cacheTime = _allStationsCacheTime;
    final cache = _allStationsCache;
    if (cache != null &&
        cacheTime != null &&
        now.difference(cacheTime) < _allStationsCacheDuration) {
      return cache;
    }

    final inFlight = _allStationsInFlight;
    if (inFlight != null) return inFlight;

    final fetchFuture = _fetchAllStationsFromPages(now);
    _allStationsInFlight = fetchFuture;
    try {
      return await fetchFuture;
    } finally {
      _allStationsInFlight = null;
    }
  }

  static Future<List<Station>> _fetchAllStationsFromPages(DateTime now) async {
    final rows = <dynamic>[];
    var start = 0;
    const pageSize = 1000;

    while (true) {
      final page = await client
          .from('istasyonlar')
          .select(_stationListSelect)
          .eq('aktif', true)
          .range(start, start + pageSize - 1);
      final pageRows = List<dynamic>.from(page);
      rows.addAll(pageRows);
      if (pageRows.length < pageSize) break;
      start += pageSize;
    }

    final stations = _parseStations(rows);
    _allStationsCache = stations;
    _allStationsCacheTime = now;
    lastAllStationsFetchError = null;
    return stations;
  }

  static Future<List<Station>> fetchAllActiveStations() {
    return _fetchAllStationsCached();
  }

  static Future<List<Station>> fetchAllActiveStationsSafe() async {
    try {
      return await _fetchAllStationsCached();
    } catch (e) {
      debugPrint('All active stations fetch failed: $e');
      lastAllStationsFetchError = 'İstasyon araması şu an yüklenemedi.';
      return const [];
    }
  }

  static List<Station> _parseStations(dynamic response) {
    final rows = List<dynamic>.from(response);
    return rows
        .whereType<Map<String, dynamic>>()
        .map(Station.fromJson)
        .where((station) => station.hasLocation)
        .toList(growable: false);
  }

  static Future<List<NewsItem>> fetchNews() async {
    try {
      final response = await client
          .from('haberler')
          .select('baslik, link, kaynak, tarih')
          .order('tarih', ascending: false)
          .limit(10);

      return List<dynamic>.from(response)
          .whereType<Map<String, dynamic>>()
          .map(NewsItem.fromJson)
          .where((news) => news.title.isNotEmpty && news.link.isNotEmpty)
          .toList(growable: false);
    } catch (e) {
      debugPrint('News fetch failed: $e');
      return [];
    }
  }
}

class _StationDistance {
  final Station station;
  final double? distanceKm;

  const _StationDistance(this.station, this.distanceKm);
}
