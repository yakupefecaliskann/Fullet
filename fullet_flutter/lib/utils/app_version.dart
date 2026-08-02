import 'package:flutter/foundation.dart';
import 'package:package_info_plus/package_info_plus.dart';

/// Uygulama sürümü için TEK kaynak.
///
/// Sürüm numarası üç ayrı yerde elle yazılıydı
/// (`app_heartbeat_service.dart`, `modern_map_screen.dart` × 2) ve hepsi
/// `'1.0.2'` sabitiydi; `pubspec.yaml` ise `1.0.2+5`. Kohort/retention
/// analizi `app_heartbeats.app_version` üzerinden yapıldığı için sürüm
/// yükseltilip bu sabitlerden biri unutulduğunda veri sessizce YANLIŞ
/// kohorta yazılırdı — ve yanlışlık ancak haftalar sonra fark edilirdi.
///
/// Artık değer `pubspec.yaml`'dan (platform paket meta verisi üzerinden)
/// okunur. `init()` uygulama açılışında bir kez çağrılır ve sonucu
/// önbelleğe alır; `current` senkron erişim ister çünkü çağıran yerler
/// (heartbeat timer'ı, ayarlar kartı) `await` edemiyor.
class AppVersion {
  /// Platform kanalı okunamazsa kullanılacak değer. Burası sürümün elle
  /// yazıldığı SON yer — güncellenmesi unutulsa bile yalnızca platform
  /// meta verisinin okunamadığı (pratikte görülmeyen) durumda devreye girer.
  static const String fallback = '1.0.2';

  static String _current = fallback;
  static bool _loaded = false;

  /// Önbelleğe alınmış sürüm (ör. `1.0.3`). `init()` çağrılmadıysa
  /// [fallback] döner.
  static String get current => _current;

  static bool get isLoaded => _loaded;

  /// pubspec sürümünü platformdan okur. Hata durumunda sessizce
  /// [fallback]'te kalır — sürüm okunamadı diye uygulama açılmamazlık
  /// etmemeli.
  static Future<void> init() async {
    try {
      final info = await PackageInfo.fromPlatform();
      if (info.version.isNotEmpty) {
        _current = info.version;
        _loaded = true;
      }
    } catch (e) {
      debugPrint('AppVersion.init failed, using fallback $fallback: $e');
    }
  }

  @visibleForTesting
  static void resetForTest() {
    _current = fallback;
    _loaded = false;
  }
}
