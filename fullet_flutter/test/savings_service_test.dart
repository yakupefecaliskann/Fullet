import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:fullet_flutter/services/savings_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('first purchase starts a 1-week streak', () async {
    await SavingsService.recordPurchase(10);
    expect(await SavingsService.getStreakWeeks(), 1);
  });

  test('second purchase in the same week does not double-count the streak',
      () async {
    await SavingsService.recordPurchase(10);
    await SavingsService.recordPurchase(5);
    expect(await SavingsService.getStreakWeeks(), 1);
  });

  test('monthly savings accumulate across multiple purchases', () async {
    await SavingsService.recordPurchase(10);
    await SavingsService.recordPurchase(5.5);
    expect(await SavingsService.getCurrentMonthSavings(), 15.5);
  });

  test('no purchase yet means no streak', () async {
    expect(await SavingsService.getStreakWeeks(), 0);
  });
}
