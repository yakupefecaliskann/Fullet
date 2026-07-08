import 'package:shared_preferences/shared_preferences.dart';

const _streakLastWeekKey = 'savings_streak_last_week_start';
const _streakCountKey = 'savings_streak_weeks';

/// smart_station_service.dart'taki savingsTL, bu istasyonun (seçilen ay
/// tanımlı en iyi alternatife göre) tahmini maliyet farkını verir —
/// gerçek tüketim doğrulaması yok. "Buradan aldım" aksiyonunda bu değer
/// aylık bir toplama eklenir; UI her zaman "tahmini" etiketiyle gösterir,
/// kesin bir rakammış gibi sunulmaz.
class SavingsService {
  static String _monthKey(DateTime d) =>
      'savings_estimate_${d.year}_${d.month.toString().padLeft(2, '0')}';

  /// Pazartesi başlangıçlı hafta anahtarı (yyyy-MM-dd) — takvim haftası
  /// sınırını basitçe ve tutarlı biçimde belirlemek için.
  static DateTime _weekStart(DateTime d) {
    final dateOnly = DateTime(d.year, d.month, d.day);
    return dateOnly.subtract(Duration(days: dateOnly.weekday - 1));
  }

  static Future<void> recordPurchase(double savingsTL) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _monthKey(DateTime.now());
    final current = prefs.getDouble(key) ?? 0;
    await prefs.setDouble(key, current + savingsTL);
    await _recordStreakAction(prefs);
  }

  static Future<void> _recordStreakAction(SharedPreferences prefs) async {
    final currentWeekStart = _weekStart(DateTime.now());
    final lastWeekStr = prefs.getString(_streakLastWeekKey);
    final lastWeek = lastWeekStr != null ? DateTime.parse(lastWeekStr) : null;

    if (lastWeek != null && lastWeek == currentWeekStart) {
      return; // bu hafta zaten sayıldı
    }

    final int newStreak;
    if (lastWeek != null &&
        currentWeekStart.difference(lastWeek).inDays == 7) {
      newStreak = (prefs.getInt(_streakCountKey) ?? 0) + 1;
    } else {
      newStreak = 1; // ilk aksiyon veya haftalar arası boşluk var
    }

    await prefs.setString(
        _streakLastWeekKey, currentWeekStart.toIso8601String());
    await prefs.setInt(_streakCountKey, newStreak);
  }

  static Future<double> getCurrentMonthSavings() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getDouble(_monthKey(DateTime.now())) ?? 0;
  }

  /// Üst üste "Buradan Aldım" işaretlenen hafta sayısı. Son işaretlemenin
  /// üzerinden bir haftadan fazla boşluk geçtiyse seri bozulmuş sayılır (0).
  static Future<int> getStreakWeeks() async {
    final prefs = await SharedPreferences.getInstance();
    final lastWeekStr = prefs.getString(_streakLastWeekKey);
    if (lastWeekStr == null) return 0;

    final lastWeek = DateTime.parse(lastWeekStr);
    final currentWeekStart = _weekStart(DateTime.now());
    if (currentWeekStart.difference(lastWeek).inDays > 7) return 0;

    return prefs.getInt(_streakCountKey) ?? 0;
  }
}
