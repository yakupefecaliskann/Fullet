import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest.dart' as tz_data;

import 'analytics_service.dart';

const _fuelReminderEnabledKey = 'fuel_reminder_enabled';
const _fuelReminderTargetAtKey = 'fuel_reminder_target_at';

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
    if (response.actionId == _premiumInterestActionId) {
      AnalyticsService.logPremiumInterestClicked(
        source: 'price_alert_notification',
      );
      return;
    }
    AnalyticsService.logNotificationOpened(
      notificationId: response.id ?? 0,
      payload: response.payload ?? '',
    );
  }

  static const _premiumInterestActionId = 'premium_interest';

  /// Fiyat alarmı tetiklendiğinde anlık (zamanlamasız) bildirim gösterir.
  /// [id] alarmın kendine özgü bir hash'i olmalı ki aynı alarm tekrar
  /// tetiklenene kadar bildirim kanalında üst üste binmesin.
  ///
  /// Bildirimde gerçek ödeme entegrasyonu olmadan bir premium-talep ölçüm
  /// aksiyonu ("İlgileniyorum ⭐") da gösterilir — Aşama 4 büyüme deneyi,
  /// bkz. plan dosyası "Premium hook".
  static Future<void> showPriceAlertNotification({
    required int id,
    required String title,
    required String body,
    required String payload,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      'price_alert',
      'Fiyat Alarmı',
      channelDescription: 'Kişisel fiyat alarmı bildirimleri',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
      actions: [
        AndroidNotificationAction(
          _premiumInterestActionId,
          'İlgileniyorum ⭐',
        ),
      ],
    );

    await _plugin.show(
      id,
      title,
      body,
      const NotificationDetails(android: androidDetails),
      payload: payload,
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

  static Future<void> cancelFuelReminder() async =>
      _plugin.cancel(NotificationIds.fuelReminder);

  static Future<bool> areNotificationsEnabled() async {
    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    return await android?.areNotificationsEnabled() ?? false;
  }

  static Future<bool> isFuelReminderEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_fuelReminderEnabledKey) ?? true;
  }

  /// Kullanıcı Ayarlar'dan hatırlatıcıyı açıp kapatabilir. Kapatınca
  /// bekleyen bildirim iptal edilir, açınca hemen yeniden planlanır.
  static Future<void> setFuelReminderEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_fuelReminderEnabledKey, enabled);
    if (enabled) {
      await prefs.remove(_fuelReminderTargetAtKey);
      await ensureFuelReminderScheduled();
    } else {
      await cancelFuelReminder();
      await prefs.remove(_fuelReminderTargetAtKey);
    }
  }

  /// Gerçek arka plan periyodikliği yerine (pil optimizasyonu riski),
  /// uygulama her ön plana geçtiğinde çağrılır: önceki hatırlatıcının
  /// hedef zamanı geçmişse (veya hiç planlanmamışsa) yeniden planlar.
  /// Bildirim izni yoksa veya kullanıcı kapattıysa hiçbir şey yapmaz.
  static Future<void> ensureFuelReminderScheduled() async {
    final prefs = await SharedPreferences.getInstance();
    if (!(prefs.getBool(_fuelReminderEnabledKey) ?? true)) return;
    if (!await areNotificationsEnabled()) return;

    final targetMs = prefs.getInt(_fuelReminderTargetAtKey);
    final now = DateTime.now();
    if (targetMs != null &&
        now.isBefore(DateTime.fromMillisecondsSinceEpoch(targetMs))) {
      return;
    }

    await scheduleFuelReminder();
    await prefs.setInt(
      _fuelReminderTargetAtKey,
      now.add(const Duration(days: 5)).millisecondsSinceEpoch,
    );
  }
}

class NotificationIds {
  static const int fuelReminder = 1;
  static const int garageReminder = 2;
}
