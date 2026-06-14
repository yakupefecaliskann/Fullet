import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:flutter/foundation.dart';

class AnalyticsService {
  static final FirebaseAnalytics _analytics = FirebaseAnalytics.instance;

  static Future<void> _log(
    String name, [
    Map<String, Object>? parameters,
  ]) async {
    try {
      await _analytics.logEvent(name: name, parameters: parameters);
    } catch (e) {
      debugPrint('Analytics event failed ($name): $e');
    }
  }

  static Future<void> logAppOpen() async {
    try {
      await _analytics.logAppOpen();
    } catch (e) {
      debugPrint('Analytics app_open failed: $e');
    }
  }

  static Future<void> logStationTapped({
    required String stationId,
    required String brand,
    required String selectedFuel,
    required double? price,
  }) =>
      _log('station_tapped', {
        'station_id': stationId,
        'brand': brand,
        'fuel_type': selectedFuel,
        'price': price ?? 0.0,
      });

  static Future<void> logFuelTypeChanged(String fuelType) =>
      _log('fuel_type_changed', {'fuel_type': fuelType});

  static Future<void> logDirectionsRequested({
    required String stationId,
    required String brand,
  }) =>
      _log('directions_requested', {
        'station_id': stationId,
        'brand': brand,
      });

  static Future<void> logGarageOpened() => _log('garage_opened');

  static Future<void> logGarageVehicleSet({
    required String make,
    required String model,
  }) =>
      _log('garage_vehicle_set', {
        'make': make,
        'model': model,
      });

  static Future<void> logGarageVehicleCleared() =>
      _log('garage_vehicle_cleared');

  static Future<void> logSearchPerformed(String query) =>
      _log('search_performed', {'query': query});

  static Future<void> logFavoriteToggled({
    required String stationId,
    required bool isFavorited,
  }) =>
      _log('favorite_toggled', {
        'station_id': stationId,
        'is_favorited': isFavorited,
      });

  static Future<void> logBrandFilterChanged(List<String> brands) =>
      _log('brand_filter_changed', {
        'brands': brands.join(','),
        'count': brands.length,
      });

  static Future<void> logFocusModeChanged(String mode) =>
      _log('focus_mode_changed', {'mode': mode});

  static Future<void> logOnboardingCompleted() => _log('onboarding_completed');

  static Future<void> logOnboardingSkipped(int step) =>
      _log('onboarding_skipped', {'at_step': step});

  static Future<void> logSmartSelectionSeen({
    required String messageType,
  }) =>
      _log('smart_selection_seen', {'message_type': messageType});

  static Future<void> logNotificationOpened({
    required int notificationId,
    required String payload,
  }) =>
      _log('notification_opened', {
        'notification_id': notificationId,
        'payload': payload,
      });
}
