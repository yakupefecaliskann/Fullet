import 'package:shared_preferences/shared_preferences.dart';

/// smart_station_service.dart'taki savingsTL, bu istasyonun (seçilen ay
/// tanımlı en iyi alternatife göre) tahmini maliyet farkını verir —
/// gerçek tüketim doğrulaması yok. "Buradan aldım" aksiyonunda bu değer
/// aylık bir toplama eklenir; UI her zaman "tahmini" etiketiyle gösterir,
/// kesin bir rakammış gibi sunulmaz.
class SavingsService {
  static String _monthKey(DateTime d) =>
      'savings_estimate_${d.year}_${d.month.toString().padLeft(2, '0')}';

  static Future<void> recordPurchase(double savingsTL) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _monthKey(DateTime.now());
    final current = prefs.getDouble(key) ?? 0;
    await prefs.setDouble(key, current + savingsTL);
  }

  static Future<double> getCurrentMonthSavings() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getDouble(_monthKey(DateTime.now())) ?? 0;
  }
}
