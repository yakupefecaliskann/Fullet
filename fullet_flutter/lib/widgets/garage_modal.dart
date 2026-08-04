import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../providers/user_preferences_provider.dart';
import '../utils/car_database.dart';
import '../theme/ful_theme.dart';
import '../services/analytics_service.dart';

/// Sıfırdan tasarlanmış Garajım paneli.
/// Araç kartı + yakıt tercihi + doluluk çubuğu + akıllı hesap.
class GarageBottomSheet extends StatefulWidget {
  final bool isDark;
  const GarageBottomSheet({super.key, this.isDark = false});

  static Future<void> show(BuildContext context, {bool isDark = false}) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (_) => GarageBottomSheet(isDark: isDark),
    );
  }

  @override
  State<GarageBottomSheet> createState() => _GarageBottomSheetState();
}

class _GarageBottomSheetState extends State<GarageBottomSheet> {
  bool _inBrandPicker = false;
  bool _inModelPicker = false;
  String? _tempBrand;
  // Pulse animasyonu kaldırıldı — SingleTickerProviderStateMixin gereksiz
  // CPU kullanımı azaltıldı

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final prefs = context.watch<UserPreferencesProvider>();
    // isDark — widget parametresinden geliyor
    final isDark = widget.isDark;

    final bg = isDark ? FulColors.darkSurface : Colors.white;
    final cardBg = isDark ? FulColors.darkCard : FulColors.lightCard;
    final border = isDark ? FulColors.darkBorder : FulColors.lightBorder;
    final textColor = isDark ? FulColors.darkText : FulColors.lightText;
    final mutedColor =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;

    if (_inBrandPicker) {
      return _buildBrandPicker(
          prefs, bg, cardBg, border, textColor, mutedColor, isDark);
    }
    if (_inModelPicker && _tempBrand != null) {
      return _buildModelPicker(
          prefs, bg, cardBg, border, textColor, mutedColor, isDark);
    }
    return _buildMain(prefs, bg, cardBg, border, textColor, mutedColor, isDark);
  }

  // ─────────────────────────────────────────────────────────────
  // Ana Ekran
  // ─────────────────────────────────────────────────────────────
  Widget _buildMain(UserPreferencesProvider prefs, Color bg, Color cardBg,
      Color border, Color textColor, Color mutedColor, bool isDark) {
    final hasCar = prefs.selectedMake != null && prefs.selectedModel != null;
    final fuelColor = _fuelColor(prefs.selectedFuel);

    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(bottom: 18),
            decoration: BoxDecoration(
                color: border, borderRadius: BorderRadius.circular(99)),
          ),

          // ── Başlık ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Garajım',
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 28,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.5,
                  color: textColor,
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: fuelColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(99),
                ),
                child: Row(
                  children: [
                    Icon(Icons.local_gas_station_rounded,
                        size: 14, color: fuelColor),
                    const SizedBox(width: 4),
                    Text(
                      prefs.selectedFuel,
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: fuelColor,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // ── Araç Kartı ──
          GestureDetector(
            onTap: () {
              HapticFeedback.lightImpact();
              setState(() => _inBrandPicker = true);
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: double.infinity,
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                gradient: hasCar
                    ? LinearGradient(
                        colors: [
                          fuelColor.withValues(alpha: isDark ? 0.3 : 0.5),
                          fuelColor.withValues(alpha: isDark ? 0.1 : 0.35),
                        ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: hasCar ? null : cardBg,
                borderRadius: BorderRadius.circular(28),
                boxShadow: hasCar
                    ? [
                        BoxShadow(
                          color: fuelColor.withValues(alpha: 0.3),
                          blurRadius: 24,
                          offset: const Offset(0, 10),
                        )
                      ]
                    : [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.04),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        )
                      ],
              ),
              child: hasCar
                  ? _CarInfo(
                      brand: prefs.selectedMake!,
                      model: prefs.selectedModel!,
                      fuel: prefs.selectedFuel,
                      fuelColor: isDark ? fuelColor : Colors.white,
                      textColor: isDark ? Colors.white : Colors.white,
                      mutedColor: Colors.white70,
                    )
                  : _EmptyCarSlot(textColor: textColor, mutedColor: mutedColor),
            ),
          ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.15, end: 0),

          // Aracı kaldır butonu — sadece araç seçiliyse görünür
          if (hasCar) ...[
            const SizedBox(height: 8),
            GestureDetector(
              onTap: () {
                HapticFeedback.lightImpact();
                prefs.clearVehicle();
                AnalyticsService.logGarageVehicleCleared();
              },
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.delete_outline_rounded,
                        size: 16, color: Colors.red.withValues(alpha: 0.7)),
                    const SizedBox(width: 6),
                    Text(
                      'Aracımı kaldır',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: Colors.red.withValues(alpha: 0.7),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 24),

          // ── Yakıt Tipi Seçici ──
          _FuelSelector(
            selected: prefs.selectedFuel,
            onSelect: (f) {
              HapticFeedback.lightImpact();
              prefs.setSelectedFuel(f);
            },
            isDark: isDark,
            border: border,
          ).animate().fadeIn(duration: 400.ms, delay: 80.ms),

          const SizedBox(height: 16),

          // ── Depo + Tüketim ──
          Row(
            children: [
              Expanded(
                child: _ValueCard(
                  icon: Icons.local_gas_station_rounded,
                  label: 'Depo',
                  value: '${prefs.tankCapacity.toStringAsFixed(0)} L',
                  color: fuelColor,
                  cardBg: cardBg,
                  border: border,
                  textColor: textColor,
                  mutedColor: mutedColor,
                  onTap: () => _showSlider(
                    context,
                    'Depo Kapasitesi (L)',
                    prefs.tankCapacity,
                    20,
                    120,
                    (v) => prefs.updateTankCapacity(v),
                    color: fuelColor,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _ValueCard(
                  icon: Icons.speed_rounded,
                  label: 'Tüketim',
                  value: '${prefs.fuelConsumption.toStringAsFixed(1)} L/100',
                  color: FulColors.info,
                  cardBg: cardBg,
                  border: border,
                  textColor: textColor,
                  mutedColor: mutedColor,
                  onTap: () => _showSlider(
                    context,
                    'Yakıt Tüketimi (L/100km)',
                    prefs.fuelConsumption,
                    3,
                    20,
                    (v) => prefs.updateFuelConsumption(v),
                    color: FulColors.info,
                    divisions: 34,
                  ),
                ),
              ),
            ],
          ).animate().fadeIn(duration: 400.ms, delay: 120.ms),

          const SizedBox(height: 16),

          // ── Hesap özeti ──
          if (hasCar)
            _SummaryCard(
              prefs: prefs,
              fuelColor: fuelColor,
              isDark: isDark,
              cardBg: cardBg,
              border: border,
              textColor: textColor,
              mutedColor: mutedColor,
            ).animate().fadeIn(duration: 400.ms, delay: 160.ms),

          const SizedBox(height: 20),

          // ── CTA ──
          GestureDetector(
            onTap: () {
              HapticFeedback.mediumImpact();
              Navigator.pop(context);
            },
            child: Container(
              height: 54,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [FulColors.primary, FulColors.primaryDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: FulColors.primary.withValues(alpha: 0.4),
                    blurRadius: 18,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.map_rounded, color: Colors.white, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'Haritaya Dön',
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
            ),
          ).animate().fadeIn(duration: 400.ms, delay: 200.ms),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────
  // Marka Seçici
  // ─────────────────────────────────────────────────────────────
  Widget _buildBrandPicker(
      UserPreferencesProvider prefs,
      Color bg,
      Color cardBg,
      Color border,
      Color textColor,
      Color mutedColor,
      bool isDark) {
    final makes = carDatabase.keys.toList()..sort();
    return Container(
      height: MediaQuery.of(context).size.height * 0.65,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        children: [
          _PickerHeader(
            title: 'Marka Seç',
            onBack: () => setState(() => _inBrandPicker = false),
            textColor: textColor,
            border: border,
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: makes.length,
              separatorBuilder: (_, __) => const SizedBox(height: 6),
              itemBuilder: (_, i) {
                final make = makes[i];
                return _PickerTile(
                  title: make,
                  isSelected: prefs.selectedMake == make,
                  cardBg: cardBg,
                  border: border,
                  textColor: textColor,
                  mutedColor: mutedColor,
                  onTap: () {
                    HapticFeedback.lightImpact();
                    setState(() {
                      _tempBrand = make;
                      _inBrandPicker = false;
                      _inModelPicker = true;
                    });
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────
  // Model Seçici
  // ─────────────────────────────────────────────────────────────
  Widget _buildModelPicker(
      UserPreferencesProvider prefs,
      Color bg,
      Color cardBg,
      Color border,
      Color textColor,
      Color mutedColor,
      bool isDark) {
    final models = carDatabase[_tempBrand]?.entries.toList() ?? [];
    return Container(
      height: MediaQuery.of(context).size.height * 0.65,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        children: [
          _PickerHeader(
            title: _tempBrand ?? 'Model Seç',
            onBack: () => setState(() {
              _inModelPicker = false;
              _inBrandPicker = true;
            }),
            textColor: textColor,
            border: border,
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: models.length,
              separatorBuilder: (_, __) => const SizedBox(height: 6),
              itemBuilder: (_, i) {
                final entry = models[i];
                final name = entry.key;
                final data = entry.value;
                return _PickerTile(
                  title: name,
                  subtitle:
                      '${(data["tank"] as double).toInt()} L depo • ${data["cons"]} L/100km • ${data["fuel"]}',
                  isSelected: prefs.selectedModel == name,
                  cardBg: cardBg,
                  border: border,
                  textColor: textColor,
                  mutedColor: mutedColor,
                  onTap: () {
                    HapticFeedback.lightImpact();
                    prefs.updateCarSelection(
                      _tempBrand!,
                      name,
                      tank: (data['tank'] as double?) ?? 50.0,
                      cons: (data['cons'] as double?) ?? 7.0,
                      fuel: data['fuel'] as String?,
                    );
                    AnalyticsService.logGarageVehicleSet(
                      make: _tempBrand!,
                      model: name,
                    );
                    setState(() {
                      _inModelPicker = false;
                      _tempBrand = null;
                    });
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────
  // Slider Dialog
  // ─────────────────────────────────────────────────────────────
  Future<void> _showSlider(
    BuildContext context,
    String title,
    double current,
    double min,
    double max,
    void Function(double) onChanged, {
    required Color color,
    int divisions = 20,
  }) async {
    double val = current;
    await showDialog(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, set) {
          final isDark = Theme.of(ctx).brightness == Brightness.dark;
          return AlertDialog(
            backgroundColor: isDark ? FulColors.darkSurface : Colors.white,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: Text(
              title,
              style: TextStyle(
                fontFamily: 'Outfit',
                fontWeight: FontWeight.w800,
                fontSize: 16,
                color: isDark ? FulColors.darkText : FulColors.lightText,
              ),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  val.toStringAsFixed(1),
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 32,
                    fontWeight: FontWeight.w900,
                    color: color,
                  ),
                ),
                Slider(
                  value: val,
                  min: min,
                  max: max,
                  divisions: divisions,
                  activeColor: color,
                  onChanged: (v) => set(() => val = v),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('İptal',
                    style: TextStyle(
                        fontFamily: 'Outfit', color: FulColors.lightTextMuted)),
              ),
              ElevatedButton(
                onPressed: () {
                  onChanged(val);
                  Navigator.pop(ctx);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: color,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Kaydet',
                    style: TextStyle(
                        fontFamily: 'Outfit', fontWeight: FontWeight.w800)),
              ),
            ],
          );
        },
      ),
    );
  }

  Color _fuelColor(String fuel) {
    switch (fuel) {
      case 'Motorin':
        return FulColors.info;
      case 'LPG':
        return FulColors.nearest;
      case 'Elektrik':
        return FulColors.logical;
      default:
        return FulColors.primary;
    }
  }
}

// ─────────────────────────────────────────────────────────────
// Sub-widgets
// ─────────────────────────────────────────────────────────────

class _CarInfo extends StatelessWidget {
  final String brand;
  final String model;
  final String fuel;
  final Color fuelColor;
  final Color textColor;
  final Color mutedColor;

  const _CarInfo({
    required this.brand,
    required this.model,
    required this.fuel,
    required this.fuelColor,
    required this.textColor,
    required this.mutedColor,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.2),
            shape: BoxShape.circle,
          ),
          child: const Center(
            child: Icon(
              Icons.directions_car_filled_rounded,
              size: 36,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(width: 18),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                brand,
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontWeight: FontWeight.w900,
                  fontSize: 24,
                  color: textColor,
                  height: 1,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                model,
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 16,
                  color: mutedColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.2),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.swap_horiz_rounded,
              size: 20, color: Colors.white),
        ),
      ],
    );
  }

}

class _EmptyCarSlot extends StatelessWidget {
  final Color textColor;
  final Color mutedColor;
  const _EmptyCarSlot({required this.textColor, required this.mutedColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            color: FulColors.primary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: FulColors.primary.withValues(alpha: 0.3),
              style: BorderStyle.solid,
            ),
          ),
          child: const Center(
            child: Icon(Icons.add_rounded, color: FulColors.primary, size: 28),
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Araç Ekle',
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontWeight: FontWeight.w800,
                  fontSize: 17,
                  color: textColor,
                ),
              ),
              Text(
                'Aracını seç, doğru fiyatları görelim',
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 12,
                  color: mutedColor,
                ),
              ),
            ],
          ),
        ),
        const Icon(Icons.chevron_right_rounded, color: FulColors.primary),
      ],
    );
  }
}

class _FuelSelector extends StatelessWidget {
  final String selected;
  final void Function(String) onSelect;
  final bool isDark;
  final Color border;

  const _FuelSelector({
    required this.selected,
    required this.onSelect,
    required this.isDark,
    required this.border,
  });

  @override
  Widget build(BuildContext context) {
    const fuels = [
      ('Kursunsuz 95', Icons.local_gas_station_rounded, FulColors.primary),
      ('Motorin', Icons.water_drop_rounded, FulColors.info),
      ('LPG', Icons.compress_rounded, FulColors.nearest),
      ('Elektrik', Icons.bolt_rounded, FulColors.logical),
    ];

    return Row(
      children: fuels.map((f) {
        final isSelected = selected == f.$1;
        return Expanded(
          child: GestureDetector(
            onTap: () => onSelect(f.$1),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 4),
              padding: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                color: isSelected
                    ? f.$3
                    : (isDark ? FulColors.darkSurface : Colors.white),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: isSelected ? f.$3 : border,
                  width: 1.5,
                ),
                boxShadow: isSelected
                    ? [
                        BoxShadow(
                            color: f.$3.withValues(alpha: 0.4),
                            blurRadius: 12,
                            offset: const Offset(0, 4))
                      ]
                    : [],
              ),
              child: Column(
                children: [
                  Icon(f.$2, size: 22, color: isSelected ? Colors.white : f.$3),
                  const SizedBox(height: 6),
                  Text(
                    f.$1 == 'Kursunsuz 95' ? '95' : f.$1,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 11,
                      fontWeight:
                          isSelected ? FontWeight.w900 : FontWeight.w700,
                      color: isSelected
                          ? Colors.white
                          : (isDark
                              ? FulColors.darkTextMuted
                              : FulColors.lightTextMuted),
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _ValueCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  final Color cardBg;
  final Color border;
  final Color textColor;
  final Color mutedColor;
  final VoidCallback onTap;

  const _ValueCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    required this.cardBg,
    required this.border,
    required this.textColor,
    required this.mutedColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: Container(
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
                Icon(icon, color: color, size: 16),
                const SizedBox(width: 5),
                Text(
                  label,
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 11,
                    color: mutedColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              value,
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 22,
                fontWeight: FontWeight.w900,
                color: color,
                height: 1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final UserPreferencesProvider prefs;
  final Color fuelColor;
  final bool isDark;
  final Color cardBg;
  final Color border;
  final Color textColor;
  final Color mutedColor;

  const _SummaryCard({
    required this.prefs,
    required this.fuelColor,
    required this.isDark,
    required this.cardBg,
    required this.border,
    required this.textColor,
    required this.mutedColor,
  });

  @override
  Widget build(BuildContext context) {
    final range = (prefs.tankCapacity / prefs.fuelConsumption) * 100;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'ARAÇ BİLGİLERİ',
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 10,
              letterSpacing: 1.2,
              fontWeight: FontWeight.w700,
              color: mutedColor,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _StatItem(
                  label: 'Menzil',
                  value: '${range.toStringAsFixed(0)} km',
                  color: FulColors.info,
                  textColor: textColor,
                  mutedColor: mutedColor,
                ),
              ),
              Container(width: 1, height: 40, color: border),
              Expanded(
                child: _StatItem(
                  label: 'L/100km',
                  value: prefs.fuelConsumption.toStringAsFixed(1),
                  color: FulColors.nearest,
                  textColor: textColor,
                  mutedColor: mutedColor,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  final Color textColor;
  final Color mutedColor;

  const _StatItem({
    required this.label,
    required this.value,
    required this.color,
    required this.textColor,
    required this.mutedColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 16,
              fontWeight: FontWeight.w900,
              color: color,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 10,
              color: mutedColor,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────
// Picker helpers
// ─────────────────────────────────────────────────────────────
class _PickerHeader extends StatelessWidget {
  final String title;
  final VoidCallback onBack;
  final Color textColor;
  final Color border;

  const _PickerHeader({
    required this.title,
    required this.onBack,
    required this.textColor,
    required this.border,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 14, 16, 14),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: border)),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
            onPressed: onBack,
            color: textColor,
          ),
          Text(
            title,
            style: TextStyle(
              fontFamily: 'Outfit',
              fontWeight: FontWeight.w900,
              fontSize: 18,
              color: textColor,
            ),
          ),
        ],
      ),
    );
  }
}

class _PickerTile extends StatelessWidget {
  final String title;
  final String? subtitle;
  final bool isSelected;
  final Color cardBg, border, textColor, mutedColor;
  final VoidCallback onTap;

  const _PickerTile({
    required this.title,
    this.subtitle,
    required this.isSelected,
    required this.cardBg,
    required this.border,
    required this.textColor,
    required this.mutedColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? FulColors.primary.withValues(alpha: 0.1) : cardBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? FulColors.primary : border,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                      color: isSelected ? FulColors.primary : textColor,
                    ),
                  ),
                  if (subtitle != null)
                    Text(
                      subtitle!,
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 11,
                        color: mutedColor,
                      ),
                    ),
                ],
              ),
            ),
            Icon(
              isSelected
                  ? Icons.check_circle_rounded
                  : Icons.chevron_right_rounded,
              color: isSelected ? FulColors.primary : mutedColor,
              size: 18,
            ),
          ],
        ),
      ),
    );
  }
}
