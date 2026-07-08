import 'package:flutter/material.dart';

import '../models/station.dart';
import '../services/price_alert_service.dart';
import '../theme/ful_theme.dart';

/// İstasyon detayından veya Ayarlar'dan açılır. Eşik fiyat mevcut fiyattan
/// otomatik doldurulur. Girişsiz kullanıcı için zorla giriş ekranına atmak
/// yerine iptal edilebilir, dürüst bir açıklama gösterir (alarm sunucu
/// tarafı tetikleme gerektirdiği için hesapsız kurulamaz).
class PriceAlertDialog extends StatefulWidget {
  final Station station;
  final String fuelType;
  final double? currentPrice;
  final String? currentUserId;
  final Future<void> Function()? onSignIn;
  final bool isDark;

  const PriceAlertDialog({
    super.key,
    required this.station,
    required this.fuelType,
    required this.currentPrice,
    required this.currentUserId,
    this.onSignIn,
    this.isDark = false,
  });

  static Future<void> show(
    BuildContext context, {
    required Station station,
    required String fuelType,
    required double? currentPrice,
    required String? currentUserId,
    Future<void> Function()? onSignIn,
    bool isDark = false,
  }) {
    return showDialog(
      context: context,
      builder: (_) => PriceAlertDialog(
        station: station,
        fuelType: fuelType,
        currentPrice: currentPrice,
        currentUserId: currentUserId,
        onSignIn: onSignIn,
        isDark: isDark,
      ),
    );
  }

  @override
  State<PriceAlertDialog> createState() => _PriceAlertDialogState();
}

class _PriceAlertDialogState extends State<PriceAlertDialog> {
  late final TextEditingController _thresholdController;
  bool _saving = false;
  bool _signingIn = false;

  @override
  void initState() {
    super.initState();
    _thresholdController = TextEditingController(
      text: widget.currentPrice?.toStringAsFixed(2) ?? '',
    );
  }

  @override
  void dispose() {
    _thresholdController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final uid = widget.currentUserId;
    if (uid == null) return;
    final threshold = double.tryParse(
        _thresholdController.text.replaceAll(',', '.'));
    if (threshold == null || threshold <= 0) return;

    setState(() => _saving = true);
    try {
      await PriceAlertService.createAlert(
        uid: uid,
        stationId: widget.station.id,
        fuelType: widget.fuelType,
        thresholdPrice: threshold,
      );
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Fiyat alarmı kuruldu')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Alarm kurulamadı, tekrar dene: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _signIn() async {
    setState(() => _signingIn = true);
    try {
      await widget.onSignIn?.call();
    } finally {
      if (mounted) setState(() => _signingIn = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final textColor = isDark ? FulColors.darkText : FulColors.lightText;
    final mutedColor =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;
    final bg = isDark ? FulColors.darkCard : Colors.white;

    return Dialog(
      backgroundColor: bg,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: widget.currentUserId == null
            ? _buildSignedOut(textColor, mutedColor)
            : _buildForm(textColor, mutedColor),
      ),
    );
  }

  Widget _buildSignedOut(Color textColor, Color mutedColor) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Fiyat alarmı için giriş gerekir',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.w800,
            fontSize: 17,
            color: textColor,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Alarmlar sunucu tarafında tetiklendiği için hesabına bağlanır — '
          'favoriler gibi bu da senin verinle senkronize olacak.',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 13,
            color: mutedColor,
            height: 1.4,
          ),
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Vazgeç'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton(
                onPressed: _signingIn ? null : _signIn,
                style: ElevatedButton.styleFrom(
                  backgroundColor: FulColors.primary,
                  foregroundColor: Colors.white,
                ),
                child: _signingIn
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Giriş Yap'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildForm(Color textColor, Color mutedColor) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Fiyat alarmı kur',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.w800,
            fontSize: 17,
            color: textColor,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '${widget.station.displayName} • ${widget.fuelType}',
          style: TextStyle(
              fontFamily: 'Outfit', fontSize: 12, color: mutedColor),
        ),
        const SizedBox(height: 16),
        Text(
          'Bu fiyatın altına inince haber ver',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: textColor,
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _thresholdController,
          keyboardType:
              const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(
            suffixText: '₺',
            border: OutlineInputBorder(),
            isDense: true,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Şu an 1 ücretsiz alarm hakkın var. Ek alarmlar ileride eklenecek.',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 11,
            color: mutedColor,
            fontStyle: FontStyle.italic,
          ),
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Vazgeç'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton(
                onPressed: _saving ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: FulColors.primary,
                  foregroundColor: Colors.white,
                ),
                child: _saving
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Alarmı Kur'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
