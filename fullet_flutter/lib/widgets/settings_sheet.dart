import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/price_alert.dart';
import '../models/station.dart';
import '../providers/user_preferences_provider.dart';
import '../services/notification_service.dart';
import '../services/price_alert_service.dart';
import '../services/savings_service.dart';
import '../services/supabase_service.dart';
import '../theme/ful_theme.dart';
import 'ful_side_menu.dart' show AboutSheet, AccountSection;
import 'garage_modal.dart';

/// Bağımsız Ayarlar ekranı — sürüş tercihleri, bildirimler, hesap, hakkında.
class SettingsSheet extends StatefulWidget {
  final bool isDark;
  final String appVersion;
  final User? currentUser;
  final List<Station> stations;
  final Future<void> Function()? onSignIn;
  final Future<void> Function()? onSignOut;

  const SettingsSheet({
    super.key,
    required this.isDark,
    required this.appVersion,
    required this.currentUser,
    required this.stations,
    this.onSignIn,
    this.onSignOut,
  });

  static Future<void> show(
    BuildContext context, {
    required bool isDark,
    required String appVersion,
    required User? currentUser,
    List<Station> stations = const [],
    Future<void> Function()? onSignIn,
    Future<void> Function()? onSignOut,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (_) => SettingsSheet(
        isDark: isDark,
        appVersion: appVersion,
        currentUser: currentUser,
        stations: stations,
        onSignIn: onSignIn,
        onSignOut: onSignOut,
      ),
    );
  }

  @override
  State<SettingsSheet> createState() => _SettingsSheetState();
}

class _SettingsSheetState extends State<SettingsSheet> {
  bool _fuelReminderEnabled = true;
  bool _loadingReminder = true;
  bool _deletingData = false;

  @override
  void initState() {
    super.initState();
    _loadReminderState();
  }

  Future<void> _loadReminderState() async {
    final enabled = await NotificationService.isFuelReminderEnabled();
    if (!mounted) return;
    setState(() {
      _fuelReminderEnabled = enabled;
      _loadingReminder = false;
    });
  }

  Future<void> _toggleReminder(bool value) async {
    setState(() => _fuelReminderEnabled = value);
    await NotificationService.setFuelReminderEnabled(value);
  }

  Future<void> _confirmDeleteData(
      Color textColor, Color mutedColor, Color cardBg) async {
    final user = widget.currentUser;
    if (user == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Verilerini sil'),
        content: const Text(
          'Favorilerin ve fiyat alarmların kalıcı olarak silinecek. Bu işlem geri alınamaz.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Vazgeç'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Sil', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _deletingData = true);
    try {
      await SupabaseService.deleteUserData(user.uid);
      await widget.onSignOut?.call();
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Silinemedi, tekrar dene: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _deletingData = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final bg = isDark ? const Color(0xFF0F1117) : Colors.white;
    final textColor = isDark ? FulColors.darkText : FulColors.lightText;
    final mutedColor =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;
    final cardBg = isDark ? const Color(0xFF1A1D27) : const Color(0xFFF7F8FA);
    final border = isDark ? FulColors.darkBorder : FulColors.lightBorder;
    final prefs = context.watch<UserPreferencesProvider>();

    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: border,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
            ),
            Text(
              'Ayarlar',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 22,
                fontWeight: FontWeight.w900,
                color: textColor,
              ),
            ),
            const SizedBox(height: 20),

            _SavingsSummaryCard(
              textColor: textColor,
              mutedColor: mutedColor,
              cardBg: cardBg,
              border: border,
            ),
            const SizedBox(height: 24),

            _SettingsSectionLabel('SÜRÜŞ TERCİHLERİ', mutedColor),
            const SizedBox(height: 8),
            _DrivingPrefsCard(
              prefs: prefs,
              textColor: textColor,
              mutedColor: mutedColor,
              cardBg: cardBg,
              border: border,
              onEdit: () {
                Navigator.pop(context);
                GarageBottomSheet.show(context, isDark: isDark);
              },
            ),
            const SizedBox(height: 24),

            _SettingsSectionLabel('BİLDİRİMLER', mutedColor),
            const SizedBox(height: 8),
            _NotificationToggleCard(
              enabled: _fuelReminderEnabled,
              loading: _loadingReminder,
              onChanged: _toggleReminder,
              textColor: textColor,
              mutedColor: mutedColor,
              cardBg: cardBg,
              border: border,
            ),
            if (widget.currentUser != null) ...[
              const SizedBox(height: 10),
              _PriceAlertsList(
                uid: widget.currentUser!.uid,
                stations: widget.stations,
                textColor: textColor,
                mutedColor: mutedColor,
                cardBg: cardBg,
                border: border,
              ),
            ],
            const SizedBox(height: 24),

            _SettingsSectionLabel('HESAP', mutedColor),
            const SizedBox(height: 8),
            AccountSection(
              currentUser: widget.currentUser,
              onSignIn: widget.onSignIn,
              onSignOut: widget.onSignOut,
              isDark: isDark,
              textColor: textColor,
              mutedColor: mutedColor,
              cardBg: cardBg,
              border: border,
            ),
            if (widget.currentUser != null) ...[
              const SizedBox(height: 10),
              GestureDetector(
                onTap: _deletingData
                    ? null
                    : () => _confirmDeleteData(textColor, mutedColor, cardBg),
                child: Text(
                  _deletingData ? 'Siliniyor...' : 'Verilerimi sil',
                  style: const TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFFDC2626),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),

            _SettingsSectionLabel('UYGULAMA', mutedColor),
            const SizedBox(height: 8),
            GestureDetector(
              onTap: () => showModalBottomSheet(
                context: context,
                isScrollControlled: true,
                backgroundColor: Colors.transparent,
                useSafeArea: true,
                builder: (_) => AboutSheet(
                  version: widget.appVersion,
                  isDark: isDark,
                  textColor: textColor,
                  mutedColor: mutedColor,
                  cardBg: cardBg,
                  border: border,
                ),
              ),
              child: Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 13),
                decoration: BoxDecoration(
                  color: cardBg,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline_rounded,
                        color: FulColors.primary, size: 20),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Hakkında',
                        style: TextStyle(
                          fontFamily: 'Outfit',
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: textColor,
                        ),
                      ),
                    ),
                    Icon(Icons.chevron_right_rounded,
                        size: 18, color: mutedColor),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SettingsSectionLabel extends StatelessWidget {
  final String text;
  final Color color;
  const _SettingsSectionLabel(this.text, this.color);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: TextStyle(
        fontFamily: 'Outfit',
        fontSize: 10,
        fontWeight: FontWeight.w700,
        color: color,
        letterSpacing: 1.2,
      ),
    );
  }
}

class _DrivingPrefsCard extends StatelessWidget {
  final UserPreferencesProvider prefs;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;
  final VoidCallback onEdit;

  const _DrivingPrefsCard({
    required this.prefs,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    final carLabel = prefs.hasVehicle
        ? '${prefs.selectedMake} ${prefs.selectedModel ?? ''}'.trim()
        : 'Araç seçilmedi';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  carLabel,
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                    color: textColor,
                  ),
                ),
              ),
              GestureDetector(
                onTap: onEdit,
                child: const Text(
                  'Düzenle',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                    color: FulColors.primary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Depo: ${prefs.tankCapacity.toStringAsFixed(0)} L  •  Tüketim: '
            '${prefs.fuelConsumption.toStringAsFixed(1)} L/100km',
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 12,
              color: mutedColor,
            ),
          ),
          if (!prefs.hasVehicle) ...[
            const SizedBox(height: 6),
            Text(
              'Aracın yoksa bu değerler hesaplamalarda kullanılır.',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 11,
                color: mutedColor,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _NotificationToggleCard extends StatelessWidget {
  final bool enabled;
  final bool loading;
  final ValueChanged<bool> onChanged;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const _NotificationToggleCard({
    required this.enabled,
    required this.loading,
    required this.onChanged,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Yakıt hatırlatıcısı',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    color: textColor,
                  ),
                ),
                Text(
                  'Birkaç günde bir güncel fiyatları hatırlat',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 11,
                    color: mutedColor,
                  ),
                ),
              ],
            ),
          ),
          loading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Switch(
                  value: enabled,
                  activeThumbColor: FulColors.primary,
                  onChanged: onChanged,
                ),
        ],
      ),
    );
  }
}

class _PriceAlertsList extends StatefulWidget {
  final String uid;
  final List<Station> stations;
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const _PriceAlertsList({
    required this.uid,
    required this.stations,
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  State<_PriceAlertsList> createState() => _PriceAlertsListState();
}

class _PriceAlertsListState extends State<_PriceAlertsList> {
  late Future<List<PriceAlert>> _future;

  @override
  void initState() {
    super.initState();
    _future = PriceAlertService.getUserAlerts(widget.uid);
  }

  Future<void> _delete(String alertId) async {
    await PriceAlertService.deleteAlert(alertId);
    if (!mounted) return;
    setState(() {
      _future = PriceAlertService.getUserAlerts(widget.uid);
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<PriceAlert>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const SizedBox.shrink();
        }
        final alerts = snapshot.data ?? const [];
        if (alerts.isEmpty) return const SizedBox.shrink();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: alerts.map((alert) {
            final station = widget.stations
                .where((s) => s.id == alert.stationId)
                .cast<Station?>()
                .firstWhere((s) => true, orElse: () => null);
            return Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: widget.cardBg,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: widget.border),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          station?.displayName ?? 'İstasyon',
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                            color: widget.textColor,
                          ),
                        ),
                        Text(
                          '${alert.fuelType} ≤ ${alert.thresholdPrice.toStringAsFixed(2)} ₺',
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 11,
                            color: widget.mutedColor,
                          ),
                        ),
                      ],
                    ),
                  ),
                  GestureDetector(
                    onTap: () => _delete(alert.id),
                    child: Icon(Icons.delete_outline_rounded,
                        size: 20, color: widget.mutedColor),
                  ),
                ],
              ),
            );
          }).toList(),
        );
      },
    );
  }
}

/// "Buradan Aldım" ile biriktirilen tahmini tasarrufu gösterir. Gerçek
/// tüketim doğrulaması yapılmadığı için etiket açıkça "tahmini" der —
/// kesin bir rakammış gibi sunulmaz.
class _SavingsSummaryCard extends StatefulWidget {
  final Color textColor;
  final Color mutedColor;
  final Color cardBg;
  final Color border;

  const _SavingsSummaryCard({
    required this.textColor,
    required this.mutedColor,
    required this.cardBg,
    required this.border,
  });

  @override
  State<_SavingsSummaryCard> createState() => _SavingsSummaryCardState();
}

class _SavingsSummaryCardState extends State<_SavingsSummaryCard> {
  late final Future<double> _future = SavingsService.getCurrentMonthSavings();
  late final Future<int> _streakFuture = SavingsService.getStreakWeeks();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<double>(
      future: _future,
      builder: (context, snapshot) {
        final savings = snapshot.data ?? 0;
        if (snapshot.connectionState != ConnectionState.done ||
            savings <= 0) {
          return const SizedBox.shrink();
        }
        return Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: widget.cardBg,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: widget.border),
          ),
          child: Row(
            children: [
              const Text('💰', style: TextStyle(fontSize: 22)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Bu ay tahmini ${savings.toStringAsFixed(0)} ₺ tasarruf ettin',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontWeight: FontWeight.w800,
                        fontSize: 14,
                        color: widget.textColor,
                      ),
                    ),
                    Text(
                      'Tahmini — gerçek tüketimini doğrulamıyoruz',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 11,
                        color: widget.mutedColor,
                      ),
                    ),
                    FutureBuilder<int>(
                      future: _streakFuture,
                      builder: (context, streakSnapshot) {
                        final streak = streakSnapshot.data ?? 0;
                        if (streak < 2) return const SizedBox.shrink();
                        return Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            '🔥 $streak hafta üst üste takip ettin',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontWeight: FontWeight.w700,
                              fontSize: 11,
                              color: widget.textColor,
                            ),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
