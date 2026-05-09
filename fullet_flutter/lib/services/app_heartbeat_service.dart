import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'supabase_service.dart';

class AppHeartbeatService {
  static const _installIdKey = 'fullet_install_id';
  static const _appVersion = '1.0.1';
  static const _heartbeatInterval = Duration(minutes: 15);
  static Timer? _timer;
  static bool _isSending = false;

  static void start() {
    unawaited(sendHeartbeat());
    _timer ??= Timer.periodic(_heartbeatInterval, (_) {
      unawaited(sendHeartbeat());
    });
  }

  static Future<void> sendHeartbeat() async {
    if (_isSending) return;
    _isSending = true;
    try {
      final installId = await _installId();
      await SupabaseService.client.rpc('record_app_heartbeat', params: {
        'p_install_id': installId,
        'p_app_version': _appVersion,
        'p_platform': defaultTargetPlatform.name,
      });
    } catch (error) {
      debugPrint('App heartbeat skipped: $error');
    } finally {
      _isSending = false;
    }
  }

  static Future<String> _installId() async {
    final prefs = await SharedPreferences.getInstance();
    final existing = prefs.getString(_installIdKey);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final generated = _uuidV4();
    await prefs.setString(_installIdKey, generated);
    return generated;
  }

  static String _uuidV4() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final hex = bytes.map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
    return [
      hex.substring(0, 8),
      hex.substring(8, 12),
      hex.substring(12, 16),
      hex.substring(16, 20),
      hex.substring(20),
    ].join('-');
  }
}
