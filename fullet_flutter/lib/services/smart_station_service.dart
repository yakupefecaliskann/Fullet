import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../models/station.dart';
import '../utils/distance_calculator.dart';

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
    String? mostLogicalStationId;
    double bestTotalCost = double.infinity;

    for (final station in stations) {
      final price = station.trustedPriceValueFor(selectedFuel);
      if (price == null || !price.isFinite || price <= 0) continue;

      if (price < cheapestPrice) {
        cheapestPrice = price;
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

    final price = station.trustedPriceValueFor(selectedFuel);
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
