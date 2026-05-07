import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/user_preferences_provider.dart';
import '../utils/car_database.dart';

class GarageModal extends StatefulWidget {
  const GarageModal({super.key});

  static void show(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Padding(
        padding:
            EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: const GarageModal(),
      ),
    );
  }

  @override
  State<GarageModal> createState() => _GarageModalState();
}

class _GarageModalState extends State<GarageModal> {
  String? pickerMode; // 'make' or 'model'

  @override
  Widget build(BuildContext context) {
    final prefs = context.watch<UserPreferencesProvider>();

    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF111827),
        borderRadius: BorderRadius.only(
            topLeft: Radius.circular(32), topRight: Radius.circular(32)),
        border: Border(top: BorderSide(color: Color(0xFF1F2937))),
      ),
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 40),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.directions_car_rounded,
                      color: Color(0xFF10B981), size: 26),
                  SizedBox(width: 8),
                  Text('Garajım',
                      style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF10B981),
                          letterSpacing: 0.5)),
                ],
              ),
              GestureDetector(
                onTap: () {
                  if (pickerMode != null) {
                    setState(() => pickerMode = null);
                  } else {
                    Navigator.pop(context);
                  }
                },
                child: Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                      color: const Color(0xFFF3F4F6),
                      borderRadius: BorderRadius.circular(20)),
                  child: const Icon(Icons.close_rounded,
                      color: Color(0xFF666666), size: 20),
                ),
              )
            ],
          ),
          const SizedBox(height: 8),
          const Text('Aracınızı seçin, gerisini asistanınıza bırakın.',
              style: TextStyle(
                  fontSize: 13, color: Color(0xFF9CA3AF), height: 1.4)),
          const SizedBox(height: 20),
          if (pickerMode == 'make') ...[
            SizedBox(
              height: 380,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  GestureDetector(
                    onTap: () => setState(() => pickerMode = null),
                    child: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Text('← Vazgeç',
                          style: TextStyle(
                              color: Color(0xFF10B981),
                              fontSize: 16,
                              fontWeight: FontWeight.bold)),
                    ),
                  ),
                  Expanded(
                    child: ListView.builder(
                      itemCount: carDatabase.keys.length,
                      itemBuilder: (context, index) {
                        final make = carDatabase.keys.elementAt(index);
                        return GestureDetector(
                          onTap: () {
                            prefs.updateCarSelection(make, null);
                            setState(() => pickerMode = null);
                          },
                          child: Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                                color: const Color(0xFF1F2937),
                                borderRadius: BorderRadius.circular(12),
                                border:
                                    Border.all(color: const Color(0xFF374151))),
                            child: Text(make,
                                style: const TextStyle(
                                    color: Color(0xFFE5E7EB),
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600)),
                          ),
                        );
                      },
                    ),
                  )
                ],
              ),
            )
          ] else if (pickerMode == 'model') ...[
            SizedBox(
              height: 380,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  GestureDetector(
                    onTap: () => setState(() => pickerMode = null),
                    child: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Text('← Vazgeç',
                          style: TextStyle(
                              color: Color(0xFF10B981),
                              fontSize: 16,
                              fontWeight: FontWeight.bold)),
                    ),
                  ),
                  Expanded(
                    child: ListView.builder(
                      itemCount:
                          carDatabase[prefs.selectedMake]?.keys.length ?? 0,
                      itemBuilder: (context, index) {
                        final model = carDatabase[prefs.selectedMake]!
                            .keys
                            .elementAt(index);
                        return GestureDetector(
                          onTap: () {
                            final data =
                                carDatabase[prefs.selectedMake]![model]!;
                            prefs.updateCarSelection(prefs.selectedMake!, model,
                                tank: data['tank'],
                                cons: data['cons'],
                                fuel: data['fuel']);
                            setState(() => pickerMode = null);
                          },
                          child: Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                                color: const Color(0xFF1F2937),
                                borderRadius: BorderRadius.circular(12),
                                border:
                                    Border.all(color: const Color(0xFF374151))),
                            child: Text(model,
                                style: const TextStyle(
                                    color: Color(0xFFE5E7EB),
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600)),
                          ),
                        );
                      },
                    ),
                  )
                ],
              ),
            )
          ] else ...[
            Row(
              children: [
                Expanded(
                  child: GestureDetector(
                    onTap: () => setState(() => pickerMode = 'make'),
                    child: Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                          color: const Color(0xFF1F2937),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: const Color(0xFF374151))),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('MARKANIZ',
                              style: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF9CA3AF),
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.5)),
                          const SizedBox(height: 8),
                          Text(prefs.selectedMake ?? 'Seçin',
                              style: const TextStyle(
                                  fontSize: 16,
                                  color: Color(0xFF10B981),
                                  fontWeight: FontWeight.w900)),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: GestureDetector(
                    onTap: prefs.selectedMake == null
                        ? null
                        : () => setState(() => pickerMode = 'model'),
                    child: Opacity(
                      opacity: prefs.selectedMake == null ? 0.5 : 1.0,
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                            color: const Color(0xFF1F2937),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: const Color(0xFF374151))),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('MODELİNİZ',
                                style: TextStyle(
                                    fontSize: 12,
                                    color: Color(0xFF9CA3AF),
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.5)),
                            const SizedBox(height: 8),
                            Text(prefs.selectedModel ?? 'Seçin',
                                style: const TextStyle(
                                    fontSize: 16,
                                    color: Color(0xFF10B981),
                                    fontWeight: FontWeight.w900)),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: const Color(0xFF1F2937),
                  borderRadius: BorderRadius.circular(24)),
              child: Column(
                children: [
                  _buildStepperRow(
                      'Depo Hacmi (L)',
                      prefs.tankCapacity.toStringAsFixed(0),
                      () => prefs.updateTankCapacity(
                          (prefs.tankCapacity - 1).clamp(10, 200).toDouble()),
                      () => prefs.updateTankCapacity(
                          (prefs.tankCapacity + 1).clamp(10, 200).toDouble())),
                  const Divider(color: Color(0xFF374151), height: 1),
                  _buildStepperRow(
                      'Şehir İçi (L/100km)',
                      prefs.fuelConsumption.toStringAsFixed(1),
                      () => prefs.updateFuelConsumption(
                          (prefs.fuelConsumption - 0.1).clamp(1.0, 30.0)),
                      () => prefs.updateFuelConsumption(
                          (prefs.fuelConsumption + 0.1).clamp(1.0, 30.0))),
                  const SizedBox(height: 16),
                  const Text('YAKIT TİPİ',
                      style: TextStyle(
                          fontSize: 14,
                          color: Color(0xFF9CA3AF),
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5)),
                  const SizedBox(height: 12),
                  Container(
                    decoration: BoxDecoration(
                        color: const Color(0xFF374151),
                        borderRadius: BorderRadius.circular(14)),
                    padding: const EdgeInsets.all(4),
                    child: Row(
                      children: ['Kursunsuz 95', 'Motorin', 'LPG'].map((fuel) {
                        final isActive = prefs.selectedFuel == fuel;
                        return Expanded(
                          child: GestureDetector(
                            onTap: () => prefs.updateSelectedFuel(fuel),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 250),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              decoration: BoxDecoration(
                                color: isActive
                                    ? const Color(0xFF10B981)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                fuel == 'Kursunsuz 95' ? 'Benzin' : fuel,
                                style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 13,
                                  color: isActive
                                      ? const Color(0xFF111827)
                                      : const Color(0xFF9CA3AF),
                                ),
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  )
                ],
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF10B981),
                padding: const EdgeInsets.symmetric(vertical: 18),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20)),
                elevation: 8,
                shadowColor: const Color(0xFF10B981).withOpacity(0.4),
              ),
              child: const Text('Güncelle ve Kapat',
                  style: TextStyle(
                      color: Color(0xFF111827),
                      fontWeight: FontWeight.w900,
                      fontSize: 17,
                      letterSpacing: 0.5)),
            )
          ]
        ],
      ),
    );
  }

  Widget _buildStepperRow(
      String label, String value, VoidCallback onMinus, VoidCallback onPlus) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 14),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 15,
                  color: Color(0xFFE5E7EB),
                  fontWeight: FontWeight.w700)),
          Container(
            decoration: BoxDecoration(
                color: const Color(0xFF374151),
                borderRadius: BorderRadius.circular(14)),
            clipBehavior: Clip.antiAlias,
            child: Row(
              children: [
                GestureDetector(
                  onTap: onMinus,
                  child: Container(
                    width: 40,
                    height: 40,
                    color: const Color(0xFF4B5563),
                    child: const Center(
                        child: Text('-',
                            style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: Colors.white))),
                  ),
                ),
                SizedBox(
                  width: 65,
                  child: Center(
                      child: Text(value,
                          style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF10B981)))),
                ),
                GestureDetector(
                  onTap: onPlus,
                  child: Container(
                    width: 40,
                    height: 40,
                    color: const Color(0xFF4B5563),
                    child: const Center(
                        child: Text('+',
                            style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: Colors.white))),
                  ),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }
}
