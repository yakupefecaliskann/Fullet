import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../models/station.dart';
import '../utils/distance_calculator.dart';
import '../utils/price_formatter.dart';

class SmartStationResult {
  final String? cheapestStationId;
  final String? mostLogicalStationId;
  final double bestTotalCost;

  SmartStationResult({
    this.cheapestStationId,
    this.mostLogicalStationId,
    required this.bestTotalCost,
  });
}

class SmartScore {
  final double score; // 0-100
  final double savingsTL; // pozitif = kazanç, negatif = kayıp
  final double distanceKm;
  final double pricePerLiter;
  final String category; // 'best', 'good', 'ok', 'poor'

  const SmartScore({
    required this.score,
    required this.savingsTL,
    required this.distanceKm,
    required this.pricePerLiter,
    required this.category,
  });
}

class SmartStationService {
  static SmartStationResult calculateBestStations({
    required LatLng location,
    required List<Station> stations,
    required String selectedFuel,
    required double tankCapacity,
    required double fuelConsumption,
  }) {
    String? cheapestStationId;
    double cheapestPrice = double.infinity;
    int cheapestRank = priceStatusRank(null);
    String? mostLogicalStationId;
    double bestTotalCost = double.infinity;

    for (final station in stations) {
      // S2-2: haritada gösterilen havuzun aynısı (fresh + stale).
      final price = station.priceValueFor(selectedFuel);
      if (price == null || !price.isFinite || price <= 0) continue;

      // Madde 21: `low_priority` istasyon TAÇ ALAMAZ. Bu durum "7 gündür
      // hiçbir bot bu kaydı doğrulamadı" demek (pg_cron JOB 3) — konumu veya
      // varlığı şüpheli. Kullanıcıyı böyle bir istasyona yönlendirmek, en
      // ucuzu bulmanın değil yanlış yere göndermenin yoludur. Haritada
      // görünmeye devam eder, sadece soluk ve tavsiye edilmez.
      if (station.isLowPriority) continue;

      final rank = priceStatusRank(station.priceStatusFor(selectedFuel));
      // Fiyat eşitse taze olan kazansın; bayat yalnızca gerçekten daha ucuzsa
      // tacı alır.
      if (price < cheapestPrice ||
          (price == cheapestPrice && rank < cheapestRank)) {
        cheapestPrice = price;
        cheapestRank = rank;
        cheapestStationId = station.id;
      }

      final distance = getDistanceKm(
        location.latitude,
        location.longitude,
        station.latitude,
        station.longitude,
      );
      if (distance == null) continue;

      final costToFill = tankCapacity * price;
      final travelCost = distance * (fuelConsumption / 100) * price;
      final totalCost = costToFill + travelCost;

      if (totalCost < bestTotalCost) {
        bestTotalCost = totalCost;
        mostLogicalStationId = station.id;
      }
    }

    return SmartStationResult(
      cheapestStationId: cheapestStationId,
      mostLogicalStationId: mostLogicalStationId,
      bestTotalCost: bestTotalCost,
    );
  }

  static SmartScore? calculateSmartScore({
    required Station station,
    required LatLng location,
    required String selectedFuel,
    required double tankCapacity,
    required double fuelConsumption,
    required SmartStationResult bestResult,
  }) {
    final lat = station.latitude;
    final lng = station.longitude;
    if (lat == null || lng == null) return null;

    // S2-2: calculateBestStations ile aynı havuz.
    final price = station.priceValueFor(selectedFuel);
    if (price == null) return null;

    final distanceKm =
        getDistanceKm(location.latitude, location.longitude, lat, lng);
    if (distanceKm == null) return null;

    final myTotalCost =
        (tankCapacity * price) + (distanceKm * (fuelConsumption / 100) * price);

    // bestTotalCost sonsuzsa bu tek fiyatlı istasyon — otomatik best
    final effectiveBest = bestResult.bestTotalCost.isInfinite
        ? myTotalCost
        : bestResult.bestTotalCost;
    final savingsTL = effectiveBest - myTotalCost;

    // 50 TL kayıp = skor 0, en iyi = skor 100
    const maxLoss = 50.0;
    final normalizedLoss = (-savingsTL).clamp(0.0, maxLoss);
    final score =
        ((maxLoss - normalizedLoss) / maxLoss * 100).clamp(0.0, 100.0);

    final String category;
    if (score >= 85) {
      category = 'best';
    } else if (score >= 65) {
      category = 'good';
    } else if (score >= 40) {
      category = 'ok';
    } else {
      category = 'poor';
    }

    return SmartScore(
      score: score,
      savingsTL: savingsTL,
      distanceKm: distanceKm,
      pricePerLiter: price,
      category: category,
    );
  }
}
