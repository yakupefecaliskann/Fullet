import 'package:flutter/material.dart';

import '../models/price_history.dart';
import '../theme/ful_theme.dart';
import '../utils/price_formatter.dart';

class PriceTrendSparkline extends StatelessWidget {
  final List<PriceHistory> history;
  final String selectedFuel;
  final double currentPrice;
  final bool isDark;

  const PriceTrendSparkline({
    super.key,
    required this.history,
    required this.selectedFuel,
    required this.currentPrice,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final relevant = history
        .where((h) => fuelMatches(h.fuelType, selectedFuel) && h.changedAt != null)
        .toList()
      ..sort((a, b) => a.changedAt!.compareTo(b.changedAt!));

    if (relevant.isEmpty) return const SizedBox.shrink();

    // Son 5 değişimi al (en güncel)
    final recent =
        relevant.length > 5 ? relevant.sublist(relevant.length - 5) : relevant;

    // Difference'lardan geriye doğru fiyat listesi oluştur
    double runningPrice = currentPrice;
    final prices = <double>[currentPrice];
    for (final h in recent.reversed) {
      if (h.difference != null) {
        runningPrice -= h.difference!;
        prices.insert(0, runningPrice);
      }
    }

    if (prices.length < 2) return const SizedBox.shrink();

    final isRising = prices.last > prices.first;
    final trendColor = isRising ? FulColors.danger : FulColors.logical;
    final mutedColor =
        isDark ? FulColors.darkTextMuted : FulColors.lightTextMuted;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Son değişimler',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: mutedColor,
              ),
            ),
            const SizedBox(width: 6),
            Icon(
              isRising
                  ? Icons.trending_up_rounded
                  : Icons.trending_down_rounded,
              size: 14,
              color: trendColor,
            ),
            const SizedBox(width: 3),
            Text(
              isRising ? 'Yükseliyor' : 'Düşüyor',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: trendColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 40,
          child: CustomPaint(
            painter: _SparklinePainter(prices: prices, color: trendColor),
            size: const Size(double.infinity, 40),
          ),
        ),
        const SizedBox(height: 8),
        ...recent.map((h) => _buildHistoryRow(h, mutedColor)),
      ],
    );
  }

  Widget _buildHistoryRow(PriceHistory h, Color mutedColor) {
    final diff = h.difference;
    if (diff == null) return const SizedBox.shrink();
    final isUp = diff > 0;
    final diffColor = isUp ? FulColors.danger : FulColors.logical;
    final sign = isUp ? '+' : '';
    final date = h.changedAt;
    final dateStr = date == null ? '' : _relativeDate(date);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(
            isUp ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
            size: 12,
            color: diffColor,
          ),
          const SizedBox(width: 4),
          Text(
            '$sign${diff.toStringAsFixed(2)} TL',
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: diffColor,
            ),
          ),
          const Spacer(),
          Text(
            dateStr,
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 11,
              color: mutedColor,
            ),
          ),
        ],
      ),
    );
  }

  String _relativeDate(DateTime date) {
    final diff = DateTime.now().difference(date);
    if (diff.inHours < 24) return '${diff.inHours} saat önce';
    return '${diff.inDays} gün önce';
  }
}

class _SparklinePainter extends CustomPainter {
  final List<double> prices;
  final Color color;

  _SparklinePainter({required this.prices, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    if (prices.length < 2) return;

    final paint = Paint()
      ..color = color
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final min = prices.reduce((a, b) => a < b ? a : b);
    final max = prices.reduce((a, b) => a > b ? a : b);
    final range = max - min == 0 ? 1.0 : max - min;

    final path = Path();
    for (int i = 0; i < prices.length; i++) {
      final x = i / (prices.length - 1) * size.width;
      final y = size.height - ((prices[i] - min) / range * size.height);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, paint);

    // Son nokta vurgusu
    final lastX = size.width;
    final lastY =
        size.height - ((prices.last - min) / range * size.height);
    canvas.drawCircle(
      Offset(lastX, lastY),
      3.5,
      Paint()..color = color,
    );
  }

  @override
  bool shouldRepaint(_SparklinePainter old) =>
      old.prices != prices || old.color != color;
}
