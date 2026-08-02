import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:flutter/services.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'firebase_options.dart';

import 'providers/user_preferences_provider.dart';
import 'screens/modern_map_screen.dart';
import 'screens/onboarding_screen.dart';
import 'services/analytics_service.dart';
import 'services/app_heartbeat_service.dart';
import 'services/notification_service.dart';
import 'theme/ful_theme.dart';
import 'utils/app_version.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Sürümü heartbeat'ten ÖNCE oku: app_heartbeats.app_version kohort
  // analizini besliyor, yanlış kohort verisi haftalar sonra fark edilir.
  await AppVersion.init();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.dark,
    statusBarBrightness: Brightness.light,
    systemNavigationBarColor: Colors.white,
    systemNavigationBarIconBrightness: Brightness.dark,
  ));

  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterFatalError;
    await AnalyticsService.logAppOpen();
  } catch (e) {
    debugPrint('Firebase init failed (missing config): $e');
  }

  // .env pubspec.yaml'da asset olarak listeli ama .gitignore'da: temiz bir
  // checkout + build'de dosya YOKTUR. dotenv.load o durumda fırlatır, runApp
  // hiç çağrılmaz ve kullanıcı beyaz ekran görür — hata mesajı bile yok.
  // Aşağıdaki "yüklendi ama boş" kontrolü bu asıl riskli durumu yakalamıyordu.
  try {
    await dotenv.load(fileName: '.env');
  } catch (e) {
    debugPrint('dotenv.load failed (.env asset missing?): $e');
  }

  // dotenv.env, load başarısız olduysa NotInitializedError FIRLATIR
  // (flutter_dotenv 6.0.1, dotenv.dart:39). Yalnızca load'ı try/catch'e almak
  // çökmeyi bir satır aşağı taşırdı; isInitialized kontrolü şart.
  final supabaseUrl =
      dotenv.isInitialized ? dotenv.env['SUPABASE_URL'] : null;
  final supabaseAnonKey =
      dotenv.isInitialized ? dotenv.env['SUPABASE_ANON_KEY'] : null;
  if (supabaseUrl == null ||
      supabaseUrl.isEmpty ||
      supabaseAnonKey == null ||
      supabaseAnonKey.isEmpty) {
    runApp(const _ConfigurationErrorApp());
    return;
  }

  await Supabase.initialize(
    url: supabaseUrl,
    anonKey: supabaseAnonKey,
    // Firebase, Supabase'de "Third Party Auth" sağlayıcısı olarak kayıtlı
    // olduğunda bu callback, giriş yapmış kullanıcının Firebase ID token'ını
    // her PostgREST/RPC isteğine iliştirir; auth.jwt()->>'sub' gerçek
    // firebase_uid'i döndürür ve RLS politikaları buna göre çalışabilir.
    // Giriş yapılmamışsa null döner, istek anon rolünde devam eder.
    accessToken: () async =>
        await firebase_auth.FirebaseAuth.instance.currentUser?.getIdToken(),
  );
  AppHeartbeatService.start();
  await NotificationService.initialize();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => UserPreferencesProvider()),
      ],
      child: const FulletApp(),
    ),
  );
}

class FulletApp extends StatelessWidget {
  const FulletApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Fullet',
      debugShowCheckedModeBanner: false,
      theme: FulTheme.light(),
      darkTheme: FulTheme.dark(),
      themeMode: ThemeMode.system,
      home: FutureBuilder<Widget>(
        future: _getInitialScreen(),
        builder: (context, snapshot) {
          if (snapshot.hasData) return snapshot.data!;
          return const _StartupSplash();
        },
      ),
      builder: (context, child) {
        // Tema değişince status bar rengini güncelle
        final isDark = Theme.of(context).brightness == Brightness.dark;
        return AnnotatedRegion<SystemUiOverlayStyle>(
          value: isDark
              ? const SystemUiOverlayStyle(
                  statusBarColor: Colors.transparent,
                  statusBarIconBrightness: Brightness.light,
                  systemNavigationBarColor: Color(0xFF141925),
                  systemNavigationBarIconBrightness: Brightness.light,
                )
              : const SystemUiOverlayStyle(
                  statusBarColor: Colors.transparent,
                  statusBarIconBrightness: Brightness.dark,
                  systemNavigationBarColor: Color(0xFFFFFFFF),
                  systemNavigationBarIconBrightness: Brightness.dark,
                ),
          child: child!,
        );
      },
    );
  }
}

Future<Widget> _getInitialScreen() async {
  final prefs = await SharedPreferences.getInstance();
  final onboardingDone = prefs.getBool('onboarding_done') ?? false;
  if (onboardingDone) return const ModernMapScreen();
  return const OnboardingScreen();
}

class _StartupSplash extends StatelessWidget {
  const _StartupSplash();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: FulColors.lightBackground,
      body: Center(
        child: CircularProgressIndicator(color: FulColors.primary),
      ),
    );
  }
}

class _ConfigurationErrorApp extends StatelessWidget {
  const _ConfigurationErrorApp();

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        body: Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'Fullet yapılandırması eksik. SUPABASE_URL ve SUPABASE_ANON_KEY kontrol edilmeli.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ),
    );
  }
}
