import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'supabase_service.dart';

class AuthService {
  static final _googleSignIn = GoogleSignIn();

  static User? get currentUser => FirebaseAuth.instance.currentUser;

  static Stream<User?> get authStateChanges =>
      FirebaseAuth.instance.authStateChanges();

  static Future<User?> signInWithGoogle() async {
    try {
      final account = await _googleSignIn.signIn();
      if (account == null) return null;

      final auth = await account.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: auth.accessToken,
        idToken: auth.idToken,
      );

      final result =
          await FirebaseAuth.instance.signInWithCredential(credential);
      final user = result.user;

      if (user != null) {
        await SupabaseService.upsertUserProfile(
          uid: user.uid,
          displayName: user.displayName,
          email: user.email,
          avatarUrl: user.photoURL,
        );
      }

      return user;
    } catch (_) {
      return null;
    }
  }

  static Future<void> signOut() async {
    await Future.wait([
      FirebaseAuth.instance.signOut(),
      _googleSignIn.signOut(),
    ]);
  }
}
