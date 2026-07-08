import 'package:flutter/foundation.dart';

import '../models/price_alert.dart';
import '../models/station.dart';
import 'notification_service.dart';
import 'supabase_service.dart';

/// FCM push kurulumu ayrı bir bağımlılık zinciri (Aşama 4'e bırakıldı) —
/// bu ilk sürüm dürüstçe yalnızca yerel bildirim + client-side kontrol
/// yapar: uygulama açıldığında aktif alarmlar mevcut fiyatla karşılaştırılır.
class PriceAlertService {
  static Future<List<PriceAlert>> getUserAlerts(String uid) async {
    try {
      final response = await SupabaseService.client
          .from('price_alerts')
          .select()
          .eq('user_id', uid)
          .order('olusturulma_tarihi', ascending: false);
      return List<Map<String, dynamic>>.from(response)
          .map(PriceAlert.fromJson)
          .toList();
    } catch (e) {
      debugPrint('getUserAlerts failed: $e');
      return [];
    }
  }

  static Future<void> createAlert({
    required String uid,
    required String stationId,
    required String fuelType,
    required double thresholdPrice,
  }) async {
    await SupabaseService.client.from('price_alerts').insert({
      'user_id': uid,
      'istasyon_id': stationId,
      'yakit_tipi': fuelType,
      'esik_fiyat': thresholdPrice,
    });
  }

  static Future<void> setAlertActive(String alertId, bool active) async {
    await SupabaseService.client
        .from('price_alerts')
        .update({'aktif': active}).eq('id', alertId);
  }

  static Future<void> deleteAlert(String alertId) async {
    await SupabaseService.client
        .from('price_alerts')
        .delete()
        .eq('id', alertId);
  }

  /// Uygulama her açıldığında çağrılır: kullanıcının aktif alarmlarını
  /// güncel fiyatlarla karşılaştırır, eşiğin altına inenler için yerel
  /// bildirim gösterir. Aynı alarmın her açılışta tekrar tekrar
  /// bildirim göndermemesi için son 24 saat içinde tetiklenmişse atlar.
  static Future<void> checkAlerts(String uid, List<Station> stations) async {
    try {
      final alerts = await getUserAlerts(uid);
      final stationsById = {for (final s in stations) s.id: s};
      final now = DateTime.now();

      for (final alert in alerts) {
        if (!alert.active) continue;
        if (alert.lastTriggeredAt != null &&
            now.difference(alert.lastTriggeredAt!) <
                const Duration(hours: 24)) {
          continue;
        }
        final station = stationsById[alert.stationId];
        if (station == null) continue;
        final price = station.trustedPriceValueFor(alert.fuelType);
        if (price == null || price > alert.thresholdPrice) continue;

        await NotificationService.showPriceAlertNotification(
          id: alert.id.hashCode,
          title: '${station.displayName} fiyatı düştü ⛽',
          body:
              '${alert.fuelType}: ${price.toStringAsFixed(2)} ₺ (eşik: ${alert.thresholdPrice.toStringAsFixed(2)} ₺)',
          payload: 'price_alert:${alert.stationId}',
        );
        await SupabaseService.client.from('price_alerts').update(
            {'son_tetiklenme': now.toIso8601String()}).eq('id', alert.id);
      }
    } catch (e) {
      debugPrint('checkAlerts failed: $e');
    }
  }
}
