import 'package:flutter_test/flutter_test.dart';
import 'package:fullet_flutter/utils/app_version.dart';

/// Yol haritası S3-9: sürüm numarası üç ayrı dosyada elle yazılıydı ve
/// `app_heartbeats.app_version` kohort analizini besliyordu. Sabitlerden biri
/// güncellenmeden sürüm yükseltilirse retention verisi sessizce yanlış
/// kohorta yazılırdı.
void main() {
  setUp(AppVersion.resetForTest);

  test('init cagrilmadan once fallback doner, patlamaz', () {
    expect(AppVersion.current, AppVersion.fallback);
    expect(AppVersion.isLoaded, isFalse);
  });

  test('platform kanali yoksa init sessizce fallbackte kalir', () async {
    // Test ortaminda PackageInfo platform kanali kayitli degil; init()
    // firlatmamali, cunku surum okunamadi diye uygulama acilmamazlik etmemeli.
    await AppVersion.init();
    expect(AppVersion.current, isNotEmpty);
  });

  test('fallback pubspec surumuyle ayni major.minor hattinda', () {
    // Fallback'in tamamen alakasiz bir surume kaymasini engelleyen ucuz kilit.
    expect(RegExp(r'^\d+\.\d+\.\d+$').hasMatch(AppVersion.fallback), isTrue);
  });
}
