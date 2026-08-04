import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../utils/app_log.dart';
import 'supabase_service.dart';

enum AuthResultStatus { success, cancelled, error }

/// Google girişinin sonucunu taşır. Eskiden signInWithGoogle() her hatada
/// sessizce null dönüyordu — kullanıcı "vazgeçtim" ile "ağ hatası oluştu"
/// arasındaki farkı hiç göremiyordu. Bu tip, çağıran tarafın (modern_map_screen.dart
/// onSignIn) durumu ayırt edip yalnızca gerçek hatada geri bildirim göstermesini sağlar.
class AuthResult {
  final AuthResultStatus status;
  final User? user;
  final String? message;

  const AuthResult._(this.status, {this.user, this.message});

  factory AuthResult.success(User user) =>
      AuthResult._(AuthResultStatus.success, user: user);
  factory AuthResult.cancelled() =>
      const AuthResult._(AuthResultStatus.cancelled);
  factory AuthResult.error(String message) =>
      AuthResult._(AuthResultStatus.error, message: message);

  bool get isSuccess => status == AuthResultStatus.success;
}

class AuthService {
  static final _googleSignIn = GoogleSignIn();

  static User? get currentUser => FirebaseAuth.instance.currentUser;

  static Stream<User?> get authStateChanges =>
      FirebaseAuth.instance.authStateChanges();

  static Future<AuthResult> signInWithGoogle() async {
    try {
      final account = await _googleSignIn.signIn();
      if (account == null) return AuthResult.cancelled();

      final auth = await account.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: auth.accessToken,
        idToken: auth.idToken,
      );

      final result =
          await FirebaseAuth.instance.signInWithCredential(credential);
      final user = result.user;

      if (user == null) {
        return AuthResult.error('Giriş yapılamadı, tekrar dene.');
      }

      await SupabaseService.upsertUserProfile(
        uid: user.uid,
        displayName: user.displayName,
        email: user.email,
        avatarUrl: user.photoURL,
      );

      return AuthResult.success(user);
    } catch (_) {
      return AuthResult.error('Giriş yapılamadı, tekrar dene.');
    }
  }

  /// Firebase ID token'ları varsayılan olarak Supabase'in `authenticated`
  /// Postgres rolünü atamak için aradığı `role` claim'ini içermez (bkz.
  /// Supabase Third-Party-Auth/Firebase dokümanı). Bu claim eksikse RLS'e
  /// hiç ulaşılamaz, istek sessizce `anon` (ve REVOKE sonrası: hiç) olur.
  /// Claim yoksa `set-authenticated-role` Edge Function'ını çağırıp Firebase
  /// tarafında kalıcı olarak atar, sonra token'ı zorla yeniler.
  static Future<void> ensureAuthenticatedRole(User user) async {
    try {
      final tokenResult = await user.getIdTokenResult();
      if (tokenResult.claims?['role'] == 'authenticated') return;
      await SupabaseService.client.functions
          .invoke('set-authenticated-role');
      await user.getIdToken(true);
    } catch (e) {
      appLog('ensureAuthenticatedRole failed: $e');
    }
  }

  static Future<void> signOut() async {
    await Future.wait([
      FirebaseAuth.instance.signOut(),
      _googleSignIn.signOut(),
    ]);
  }
}
