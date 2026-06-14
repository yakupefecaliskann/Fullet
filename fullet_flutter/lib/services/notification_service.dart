import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz_data;

import 'analytics_service.dart';

class NotificationService {
  static final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  static Future<void> initialize() async {
    tz_data.initializeTimeZones();

    const AndroidInitializationSettings android =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    await _plugin.initialize(
      const InitializationSettings(android: android),
      onDidReceiveNotificationResponse: _onNotificationTap,
    );
  }

  static void _onNotificationTap(NotificationResponse response) {
    AnalyticsService.logNotificationOpened(
      notificationId: response.id ?? 0,
      payload: response.payload ?? '',
    );
  }

  static Future<bool> requestPermission() async {
    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    final granted = await android?.requestNotificationsPermission();
    return granted ?? false;
  }

  /// Periyodik yakıt hatırlatıcı — 5 gün sonra sabah 09:30
  static Future<void> scheduleFuelReminder() async {
    await _plugin.cancel(NotificationIds.fuelReminder);

    final now = tz.TZDateTime.now(tz.local);
    final scheduled = tz.TZDateTime(
      tz.local,
      now.year,
      now.month,
      now.day + 5,
      9,
      30,
    );

    await _plugin.zonedSchedule(
      NotificationIds.fuelReminder,
      'Yakıt zamanı mı? ⛽',
      'Yakınındaki güncel fiyatları kontrol et',
      scheduled,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'fuel_reminder',
          'Yakıt Hatırlatıcı',
          channelDescription: 'Periyodik yakıt fiyatı hatırlatmaları',
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
          icon: '@mipmap/ic_launcher',
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      payload: 'fuel_reminder',
    );
  }

  /// Garaj kurulmamışsa 24 saat sonra hatırlatıcı
  static Future<void> scheduleGarageReminder() async {
    await _plugin.cancel(NotificationIds.garageReminder);

    final scheduled =
        tz.TZDateTime.now(tz.local).add(const Duration(hours: 24));

    await _plugin.zonedSchedule(
      NotificationIds.garageReminder,
      'Aracını henüz eklemen 🚗',
      'Garajını doldur, sana özel akıllı hesap başlasın',
      scheduled,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'garage_reminder',
          'Garaj Hatırlatıcı',
          channelDescription: 'Garaj kurulum hatırlatmaları',
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      payload: 'garage_reminder',
    );
  }

  static Future<void> cancelGarageReminder() async =>
      _plugin.cancel(NotificationIds.garageReminder);
}

class NotificationIds {
  static const int fuelReminder = 1;
  static const int garageReminder = 2;
}
