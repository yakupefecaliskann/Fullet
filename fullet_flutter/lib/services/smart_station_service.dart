import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../models/station.dart';
import '../utils/distance_calculator.dart';

class FinancialMessage {
  final String type;
  final String text;

  FinancialMessage({required this.type, required this.text});
}

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
      final price = station.priceValueFor(selectedFuel);
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

  static FinancialMessage? getFinancialMessage({
    required Station station,
    required LatLng location,
    required List<Station> stations,
    required String selectedFuel,
    required double tankCapacity,
    required double fuelConsumption,
    required SmartStationResult result,
  }) {
    final price = station.priceValueFor(selectedFuel);
    if (price == null) return null;

    final myDistance = getDistanceKm(
      location.latitude,
      location.longitude,
      station.latitude,
      station.longitude,
    );
    if (myDistance == null) return null;

    final myTotalCost =
        (tankCapacity * price) + (myDistance * (fuelConsumption / 100) * price);

    if (station.id == result.mostLogicalStationId) {
      if (result.cheapestStationId != null &&
          result.cheapestStationId != result.mostLogicalStationId) {
        final cheapStation = stations
            .where((item) => item.id == result.cheapestStationId)
            .firstOrNull;
        final cheapPrice = cheapStation?.priceValueFor(selectedFuel);
        final cheapDistance = cheapStation == null
            ? null
            : getDistanceKm(
                location.latitude,
                location.longitude,
                cheapStation.latitude,
                cheapStation.longitude,
              );

        if (cheapPrice != null && cheapDistance != null) {
          final cheapTotal = (tankCapacity * cheapPrice) +
              (cheapDistance * (fuelConsumption / 100) * cheapPrice);
          final saved = cheapTotal - myTotalCost;
          if (saved > 0) {
            return FinancialMessage(
              type: 'success',
              text:
                  'Hem Yakın Hem Karlı!\nEn ucuza gitmeye kıyasla net ${saved.toStringAsFixed(1)} TL kazandırdı.',
            );
          }
        }
      }

      return FinancialMessage(
        type: 'success',
        text:
            'En Mantıklı Seçim\nŞu an sizin için en hesaplı ve yakın istasyon.',
      );
    }

    if (station.id == result.cheapestStationId) {
      final loss = myTotalCost - result.bestTotalCost;
      return FinancialMessage(
        type: 'danger',
        text:
            'Ucuz Görünen İstasyon\nPompa ucuz ama yol masrafıyla ${loss.toStringAsFixed(1)} TL zarar edebilirsiniz.',
      );
    }

    final loss = myTotalCost - result.bestTotalCost;
    return FinancialMessage(
      type: 'warning',
      text:
          'Daha Karlısı Var\nEn mantıklı yere kıyasla ${loss.toStringAsFixed(1)} TL daha fazla masraf olur.',
    );
  }
}

extension _FirstOrNull<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
