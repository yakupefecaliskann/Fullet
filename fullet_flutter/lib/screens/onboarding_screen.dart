import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/analytics_service.dart';
import '../theme/ful_theme.dart';
import 'modern_map_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _currentPage = 0;

  static const _pages = [
    _OnboardingPage(
      icon: Icons.map_rounded,
      title: 'Yakındaki tüm fiyatlar',
      description:
          'Türkiye genelindeki güncel akaryakıt fiyatlarını tek haritada gör.',
    ),
    _OnboardingPage(
      icon: Icons.psychology_rounded,
      title: 'Sana özel akıllı seçim',
      description:
          'Aracını ekle, Fullet sadece ucuzu değil en mantıklı durağı da bulsun.',
    ),
    _OnboardingPage(
      icon: Icons.verified_rounded,
      title: 'Resmi kaynaklardan güvenilir fiyat',
      description:
          'Shell, Opet, Petrol Ofisi ve diğer resmi listelerden gelen verilerle karar ver.',
    ),
  ];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _complete({required bool openGarage}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_done', true);
    await AnalyticsService.logOnboardingCompleted();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => ModernMapScreen(openGarageOnStart: openGarage),
      ),
    );
  }

  Future<void> _skip() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_done', true);
    await AnalyticsService.logOnboardingSkipped(_currentPage);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => const ModernMapScreen()),
    );
  }

  void _next() {
    if (_currentPage == _pages.length - 1) {
      _complete(openGarage: true);
      return;
    }
    _controller.nextPage(
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [FulColors.primary, Color(0xFF0099CC)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _skip,
                  child: const Text(
                    'Atla',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
              Expanded(
                child: PageView.builder(
                  controller: _controller,
                  itemCount: _pages.length,
                  onPageChanged: (index) => setState(() {
                    _currentPage = index;
                  }),
                  itemBuilder: (context, index) {
                    final page = _pages[index];
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 30),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 92,
                            height: 92,
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.18),
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: Colors.white.withOpacity(0.35),
                              ),
                            ),
                            child:
                                Icon(page.icon, color: Colors.white, size: 44),
                          ),
                          const SizedBox(height: 28),
                          Text(
                            page.title,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontFamily: 'Outfit',
                              fontWeight: FontWeight.w900,
                              fontSize: 30,
                              height: 1.08,
                            ),
                          ),
                          const SizedBox(height: 14),
                          Text(
                            page.description,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.88),
                              fontFamily: 'Outfit',
                              fontWeight: FontWeight.w700,
                              fontSize: 16,
                              height: 1.42,
                            ),
                          ),
                        ],
                      ).animate().fadeIn(duration: 280.ms).slideY(
                          begin: 0.04,
                          end: 0,
                          duration: 280.ms,
                          curve: Curves.easeOutCubic),
                    );
                  },
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(_pages.length, (index) {
                  final selected = index == _currentPage;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    width: selected ? 24 : 8,
                    height: 8,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(selected ? 1 : 0.42),
                      borderRadius: BorderRadius.circular(999),
                    ),
                  );
                }),
              ),
              const SizedBox(height: 24),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 10),
                child: SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: FilledButton(
                    onPressed: _next,
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: FulColors.lightText,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(18),
                      ),
                    ),
                    child: Text(
                      _currentPage == _pages.length - 1
                          ? 'Aracımı ekle'
                          : 'Sonraki',
                      style: const TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ),
              ),
              if (_currentPage == _pages.length - 1)
                TextButton(
                  onPressed: _skip,
                  child: const Text(
                    'Şimdi değil, haritaya geç',
                    style: TextStyle(
                      color: Colors.white,
                      fontFamily: 'Outfit',
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              SizedBox(height: MediaQuery.of(context).padding.bottom + 14),
            ],
          ),
        ),
      ),
    );
  }
}

class _OnboardingPage {
  final IconData icon;
  final String title;
  final String description;

  const _OnboardingPage({
    required this.icon,
    required this.title,
    required this.description,
  });
}
