import 'package:flutter/foundation.dart';

/// Yaygın yanılgının aksine `debugPrint` release derlemesinde ELENMEZ —
/// logcat'e yazmaya devam eder. Supabase hata mesajları, marka fallback
/// logları ve init hataları üretim cihazlarının logunda görünür hale gelir.
///
/// Tüm teşhis logları bu yardımcıdan geçer; `kDebugMode` sabit olduğu için
/// release AOT derlemesinde gövde tamamen elenir.
void appLog(String message) {
  if (kDebugMode) {
    debugPrint(message);
  }
}
