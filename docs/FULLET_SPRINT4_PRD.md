# FULLET — SPRINT 4 PRD
## "Alarm & Bildirim" Paketi

> **Versiyon Hedefi:** 1.4.0  
> **Sprint Süresi:** ~3 hafta  
> **Karar Tarihi:** Haziran 2026

---

## Önceliklendirme Kararı (CTO)

### Değerlendirilen Adaylar

| Feature | Kullanıcı Değeri | Teknik Kolaylık | Retention | Gelir Potansiyeli | Ağırlıklı Skor |
|---------|:---:|:---:|:---:|:---:|:---:|
| Ulusal Zam/İndirim Bildirimi | 9 | 8 | 10 | 5 | **8.6** |
| Kişisel Fiyat Alarmı | 9 | 4 | 9 | 9 | **8.0** |
| Ana Ekran Widget'ı | 7 | 6 | 8 | 3 | **6.6** |
| İstasyon Yorumları | 7 | 5 | 6 | 4 | **5.8** |
| "Yolum Üzerinde" Modu | 7 | 3 | 5 | 6 | **5.4** |
| Tasarruf Geçmişi | 6 | 5 | 5 | 4 | **5.2** |

_Ağırlıklar: Kullanıcı Değeri 30% · Teknik Kolaylık 20% · Retention 35% · Gelir Potansiyeli 15%_

### Seçim Gerekçesi

İlk iki feature Sprint 4'te birlikte alındı çünkü **FCM altyapısını paylaşıyorlar** — önce S4-F1 kurulursa S4-F2 üzerine inşa edilir. Birini bırakmak altyapı kurma maliyetini iki sprinte yaymak demek.

- **Ulusal Bildirim (S4-F1):** Türkiye'de akaryakıt zamları gece yarısı duyuruluyor. Kullanıcı "zam öncesi doldurmak" için uygulamayı açmaz — ancak push gelirse açar. Retention için en güçlü kaldıraç. Altyapının %70'i zaten var (`fiyat-push` Edge Function, `push_tokens` tablosu, `send_summary_push()`).

- **Kişisel Fiyat Alarmı (S4-F2):** Premium monetizasyon hook'u. "1 alarm ücretsiz, sınırsız Premium" modeli. Kullanıcının uygulama ile aktiyi olan bir ilişki kurmasını sağlayan tek feature bu kategoride. FCM altyapısı S4-F1'de kurulduktan sonra çok daha hızlı tamamlanır.

- **Ertelenenler:** Widget kullanıcı tabanı oluştuktan sonra daha değerli. "Yolum Üzerinde" Google Directions API maliyeti nedeniyle Sprint 5+ için bekleniyor. Tasarruf Geçmişi S4-F2 ile birlikte anlam kazanır.

---

## Sprint 4 Kapsamı

```
S4-F1: FCM Kurulumu + Ulusal Fiyat Değişimi Bildirimi  (~7 gün)
S4-F2: Kişisel Fiyat Alarmı                             (~8 gün)
```

---

## S4-F1: FCM Kurulumu + Ulusal Fiyat Değişimi Bildirimi

### Problem
Uygulama pasif. Kullanıcı fiyat değişimini görmek için uygulamayı açmak zorunda. Türkiye'de akaryakıt zam/indirimleri gece yarısı yayımlanır — bu anda uygulama açılmadan bildirim gelmezse kullanıcı rakip uygulamaya geçmiştir.

### Kullanıcı Hikayesi
> "Gece yarısı zam haberi çıkınca, Fullet beni uyandırsın. Doldurmak için sabahı bekleyeyim mi yoksa hemen gideyim mi anlayayım."

### Teknik Mevcut Durum (Avantaj)

| Bileşen | Durum |
|---------|-------|
| `push_tokens` Supabase tablosu | ✅ Mevcut |
| `fiyat-push` Supabase Edge Function | ✅ Mevcut |
| `send_summary_push()` in `database_writes.py` | ✅ Mevcut ama `FULLET_PUSH_SUMMARY=0` ile kapalı |
| Flutter `firebase_messaging` paketi | ❌ Yok |
| FCM token kayıt kodu | ❌ Yok |
| Zam algılama mantığı | ❌ Yok |

### Başarı Metrikleri
- Push teslim oranı > %85 (registered token'lara)
- Bildirim sonrası app open rate > %25
- `push_tokens` tablosunda aktif kullanıcı sayısı ölçülebilir hale geldi

### Flutter Değişiklikleri

**`pubspec.yaml`:**
```yaml
firebase_messaging: ^14.7.10
```

**Yeni dosya — `lib/services/push_notification_service.dart`:**

```dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Background mesaj geldiğinde: sadece log, local notification göster
}

class PushNotificationService {
  static final _messaging = FirebaseMessaging.instance;

  static Future<void> initialize({required String? firebaseUid}) async {
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    // Bildirim izni
    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (settings.authorizationStatus == AuthorizationStatus.denied) return;

    // Token al ve kaydet
    final token = await _messaging.getToken();
    if (token != null) await _saveToken(token, firebaseUid);

    // Token yenilenince güncelle
    _messaging.onTokenRefresh.listen((t) => _saveToken(t, firebaseUid));

    // Ön plan mesajları
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);
  }

  static Future<void> _saveToken(String token, String? uid) async {
    // Supabase push_tokens tablosuna upsert
    await supabase.from('push_tokens').upsert({
      'token': token,
      'firebase_uid': uid,
      'platform': 'android',
      'olusturulma_tarihi': DateTime.now().toIso8601String(),
    }, onConflict: 'token');
  }

  static void _handleForegroundMessage(RemoteMessage message) {
    // Uygulama ön planda açıkken gelen bildirim
    // flutter_local_notifications ile göster
  }
}
```

**`lib/main.dart` değişikliği:**
```dart
// AuthService'ten uid alındıktan sonra:
await PushNotificationService.initialize(firebaseUid: authService.currentUser?.uid);
```

**`android/app/src/main/AndroidManifest.xml` değişikliği:**
```xml
<!-- Bildirim kanalı + FCM servis izni -->
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<meta-data
    android:name="com.google.firebase.messaging.default_notification_channel_id"
    android:value="fullet_fiyat"/>
```

### Backend Değişiklikleri

**`scraper/run_all_bots.py`:**
```python
# Satır 201 civarı — bot_env tanımı:
# Öncesi:
bot_env = {"FULLET_PUSH_SUMMARY": "0"}

# Sonrası (price mode'da push aktif):
push_flag = "1" if args.mode in ("prices", "all") else "0"
bot_env = {"FULLET_PUSH_SUMMARY": push_flag}
```

**`scraper/database_writes.py` — zam algılama:**

`_bulk_upsert_prices` içinde price change tracking zaten var (`float(existing.fiyat) != float(row.fiyat)`). Bu bilgi `SaveSummary` modeline taşınır ve `run_all_bots.py` sonunda değerlendirilir.

Kısa vadeli yaklaşım (Sprint 4): Fiyat değişimi olan herhangi bir major brand varsa → bildirim.
Uzun vadeli (Sprint 5): EPİAŞ/BRC verileriyle karşılaştırarak gerçek "zam/indirim" ayrımı.

```python
# database_writes.py — send_summary_push çağrılan yerde:
def send_summary_push(message: str, is_zam: bool = False) -> None:
    # Zaten var. FULLET_PUSH_SUMMARY=1 olunca aktif olur.
    ...
```

**`fiyat-push` Edge Function — doğrulama:**
Supabase Dashboard'da kontrol edilmeli:
- `push_tokens` tablosundan token'ları çekiyor mu?
- FCM Authorization header doğru mu?
- `FIREBASE_SERVER_KEY` secret set edilmiş mi?

### Kabul Kriterleri S4-F1
- [ ] Uygulama ilk açılışta bildirim izni soruyor
- [ ] Token `push_tokens` tablosuna yazılıyor
- [ ] Bot price runından sonra `push_tokens`'daki tüm cihazlara bildirim gidiyor
- [ ] Bildirim tıklanınca uygulama açılıyor
- [ ] Token yenilemede tablo güncelleniyor
- [ ] Kapalı uygulamada bildirim geliyor (background handler)

### Riskler S4-F1
| Risk | Olasılık | Etki | Önlem |
|------|---------|------|-------|
| FCM Server Key eksik/yanlış | ORTA | Bildirim gitmiyor | Supabase Edge Fn secrets kontrol |
| push_tokens RLS yetki sorunu | DÜŞÜK | Token kaydedilemiyor | Tablo izinlerini kontrol et |
| Android 13+ POST_NOTIFICATIONS izni | ORTA | Bildirim sessizce engellenir | `requestPermission()` sonucu handle et |

---

## S4-F2: Kişisel Fiyat Alarmı

### Problem
Kullanıcı "Shell Beşiktaş 48 TL'nin altına düştüğünde bildir" demek istiyor. Şu an bu mümkün değil. Bu feature kullanıcıyı uygulamaya aktif olarak bağlayan, retention ve premium monetizasyon için kritik kaldıraç.

### Kullanıcı Hikayesi
> "Gittiğim Shell istasyonunu favorilere ekledim. Kurşunsuz 95 fiyatı 48 TL'nin altına düşünce bana bildirim gelsin — o zaman doldurmaya gideyim."

### Kullanıcı Akışı
```
İstasyon bottom sheet açık
   ↓
"Fiyat Alarmı Kur" butonu  [sign-in gerekli]
   ↓
Alarm dialog → yakıt tipi seçimi + eşik fiyat girişi
   ↓
"Alarm Kur" → Supabase price_alerts tablosuna kayıt
   ↓
[6 saatte bir] alert_checker.py çalışır
   ↓
Mevcut fiyat < eşik fiyat? → FCM push gönder → alarm deaktif
   ↓
Kullanıcı bildirimi alır → uygulamayı açar → istasyona gider
```

### Başarı Metrikleri
- Alarm kuran kullanıcıların 30 günlük retention'ı ≥ 2x baseline
- Alarm tetiklenme sonrası app open rate > %40
- Premium dönüşüm funnel'ı ölçülebilir (ilk 1 alarm ücretsiz)

### Veritabanı

**`database/sprint4_price_alerts.sql`:**
```sql
CREATE TABLE IF NOT EXISTS public.price_alerts (
  id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id              TEXT NOT NULL,              -- firebase_uid
  istasyon_id          UUID REFERENCES public.istasyonlar(id) ON DELETE CASCADE,
  yakit_tipi           TEXT NOT NULL,
  esik_fiyat           DECIMAL(10, 2) NOT NULL,
  aktif                BOOLEAN DEFAULT TRUE,
  olusturulma_tarihi   TIMESTAMPTZ DEFAULT NOW(),
  son_tetiklenme       TIMESTAMPTZ,
  push_token           TEXT                        -- tetikleme anında kullanılacak token
);

CREATE INDEX IF NOT EXISTS price_alerts_aktif_idx
  ON public.price_alerts (istasyon_id, yakit_tipi) WHERE aktif = TRUE;

CREATE INDEX IF NOT EXISTS price_alerts_user_idx
  ON public.price_alerts (user_id);

-- RLS yok (mevcut fullet_favorites/fullet_users ile tutarlı)
GRANT SELECT, INSERT, UPDATE, DELETE ON public.price_alerts TO authenticated, anon;
```

### Flutter Değişiklikleri

**Yeni dosya — `lib/services/price_alert_service.dart`:**
```dart
class PriceAlertService {
  Future<void> createAlert({
    required String userId,
    required String stationId,
    required String fuelType,
    required double threshold,
    required String? pushToken,
  }) async {
    await supabase.from('price_alerts').insert({
      'user_id': userId,
      'istasyon_id': stationId,
      'yakit_tipi': fuelType,
      'esik_fiyat': threshold,
      'push_token': pushToken,
    });
  }

  Future<List<Map<String, dynamic>>> getActiveAlerts(String userId) async {
    return await supabase
        .from('price_alerts')
        .select('*, istasyonlar(marka, isim, il, ilce)')
        .eq('user_id', userId)
        .eq('aktif', true)
        .order('olusturulma_tarihi', ascending: false);
  }

  Future<void> deleteAlert(String alertId) async {
    await supabase.from('price_alerts').delete().eq('id', alertId);
  }
}
```

**Yeni widget — `lib/widgets/price_alert_dialog.dart`:**

Bottom sheet'te "Fiyat Alarmı Kur" butonuna basıldığında açılan dialog:
- Yakıt tipi seçimi (mevcut station'ın desteklediği tipler)
- Eşik fiyat input'u (mevcut fiyatı pre-fill)
- "Alarm Kur" CTA
- Sign-in değilse → "Alarm kurmak için giriş yap" mesajı + sign-in yönlendirme

**`lib/widgets/station_bottom_sheet.dart` değişikliği:**
```dart
// Yol tarifi butonunun altına ekle:
if (authService.isSignedIn) ...[
  const SizedBox(height: 8),
  OutlinedButton.icon(
    icon: const Icon(Icons.notifications_outlined),
    label: const Text('Fiyat Alarmı Kur'),
    onPressed: () => _showPriceAlertDialog(context, station),
  ),
],
```

**`lib/widgets/ful_side_menu.dart` değişikliği:**
Yan menüye "Alarmlarım" sekmesi ekle — aktif alarmların listesi, silme seçeneği.

### Backend Değişiklikleri

**Yeni dosya — `scraper/alert_checker.py`:**
```python
"""
Aktif fiyat alarmlarını kontrol eder, eşik geçildiyse push gönderir.
run_all_bots.py tarafından her price runından sonra çağrılır.
"""

from db_utils import supabase
from database_writes import send_summary_push


def check_price_alerts() -> int:
    if supabase is None:
        return 0

    # Aktif alarmları çek (istasyon ve mevcut fiyatla birlikte)
    alerts = (
        supabase.table("price_alerts")
        .select("id, user_id, istasyon_id, yakit_tipi, esik_fiyat, push_token")
        .eq("aktif", True)
        .execute()
        .data
        or []
    )

    triggered = 0
    for alert in alerts:
        # Mevcut fiyatı çek
        price_row = (
            supabase.table("fiyatlar")
            .select("fiyat, price_status")
            .eq("istasyon_id", alert["istasyon_id"])
            .eq("yakit_tipi", alert["yakit_tipi"])
            .eq("price_status", "fresh")
            .maybe_single()
            .execute()
            .data
        )
        if price_row is None:
            continue

        current_price = float(price_row["fiyat"])
        threshold = float(alert["esik_fiyat"])

        if current_price <= threshold:
            _trigger_alert(alert, current_price)
            triggered += 1

    print(f"[OK] alert_checker: {triggered}/{len(alerts)} alarm tetiklendi.")
    return triggered


def _trigger_alert(alert: dict, current_price: float) -> None:
    push_token = alert.get("push_token")
    yakit_tipi = alert["yakit_tipi"]
    threshold = alert["esik_fiyat"]

    # Kişisel push gönder (tek token'a)
    if push_token:
        _send_personal_push(
            token=push_token,
            message=f"{yakit_tipi} {current_price:.2f} TL'ye düştü — alarmınız tetiklendi!",
        )

    # Alarmı deaktif et (bir kez tetikle)
    supabase.table("price_alerts").update({
        "aktif": False,
        "son_tetiklenme": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }).eq("id", alert["id"]).execute()


def _send_personal_push(token: str, message: str) -> None:
    import os, requests
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return
    try:
        requests.post(
            f"{supabase_url}/functions/v1/fiyat-push",
            headers={"Authorization": f"Bearer {supabase_key}", "Content-Type": "application/json"},
            json={"action": "PERSONAL_PUSH", "token": token, "message": message},
            timeout=10,
        )
    except Exception as exc:
        print(f"[WARN] Personal push failed: {exc}")


if __name__ == "__main__":
    check_price_alerts()
```

**`scraper/run_all_bots.py` değişikliği:**
```python
# _run_news_bot'tan önce, prices modunda:
if args.mode in ("prices", "all"):
    print("\n=====================================")
    print("Running: alert_checker.py")
    print("=====================================")
    try:
        run_bot("alert_checker.py", env_overrides=bot_env, timeout=60, mode=args.mode)
    except Exception as exc:
        print(f"[WARN] alert_checker failed: {exc}")
```

**`fiyat-push` Edge Function güncellemesi:**

Mevcut fonksiyon büyük ihtimalle broadcast push yapıyor. `PERSONAL_PUSH` action'ı için tek token'a gönderme desteği eklenmeli:
```typescript
// Supabase Edge Function içinde:
if (body.action === "PERSONAL_PUSH" && body.token) {
  // Tek token'a FCM gönder
}
```

Bu değişiklik Supabase Dashboard üzerinden yapılır (human action).

### Kabul Kriterleri S4-F2
- [ ] Sign-in olmayan kullanıcı "Alarm Kur" butonunu görünce sign-in'e yönlendiriliyor
- [ ] Alarm kurulduğunda `price_alerts` tablosuna yazılıyor
- [ ] `alert_checker.py` mevcut fiyatı doğru karşılaştırıyor
- [ ] Eşik geçilince push bildirimi geliyor
- [ ] Alarm tetiklendikten sonra `aktif=FALSE` oluyor (tekrar tetiklenmiyor)
- [ ] "Alarmlarım" listesinde aktif/geçmiş alarmlar görünüyor
- [ ] Alarm silinebiliyor

### Riskler S4-F2
| Risk | Olasılık | Etki | Önlem |
|------|---------|------|-------|
| Bot run'da fiyat henüz güncel değilse alarm yanlış tetiklenebilir | DÜŞÜK | Yanlış bildirim | Sadece `price_status='fresh'` fiyatları kontrol et (koda dahil) |
| Kullanıcı token'ı değiştirmişse (uygulama silme/yeniden kurma) | ORTA | Bildirim gitmiyor | Token yenilemede `price_alerts.push_token` güncelle |
| PERSONAL_PUSH action fiyat-push Edge Function'da yok | YÜKSEK | Push gitmiyor | Edge Function güncellemesi human action — sprint başında yapılmalı |

---

## Supabase Değişiklikleri

| Adım | SQL/Action | Yer |
|------|-----------|-----|
| `price_alerts` tablosu | `database/sprint4_price_alerts.sql` | SQL Editor |
| `push_tokens` RLS kontrolü | Dashboard'da manual kontrol | — |
| `fiyat-push` Edge Function güncelle | Dashboard Functions editörü | Human action |
| `FIREBASE_SERVER_KEY` secret | Dashboard → Settings → Edge Functions | Human action |

---

## Değişen Dosyalar Özeti

| Dosya | Değişiklik |
|-------|-----------|
| `pubspec.yaml` | `firebase_messaging: ^14.7.10` |
| `lib/main.dart` | `PushNotificationService.initialize()` çağrısı |
| `lib/services/push_notification_service.dart` | **[YENİ]** FCM token kayıt + ön plan handler |
| `lib/services/price_alert_service.dart` | **[YENİ]** Alarm CRUD |
| `lib/widgets/price_alert_dialog.dart` | **[YENİ]** Eşik fiyat dialog'u |
| `lib/widgets/station_bottom_sheet.dart` | "Fiyat Alarmı Kur" butonu |
| `lib/widgets/ful_side_menu.dart` | "Alarmlarım" listesi |
| `android/app/src/main/AndroidManifest.xml` | FCM izni + bildirim kanalı |
| `scraper/run_all_bots.py` | `FULLET_PUSH_SUMMARY=1`, `alert_checker.py` çağrısı |
| `scraper/alert_checker.py` | **[YENİ]** Alarm checker |
| `database/sprint4_price_alerts.sql` | **[YENİ]** Tablo migration |

---

## İmplementasyon Sırası

```
Hafta 1 — S4-F1: FCM Altyapısı
├── Gün 1: firebase_messaging paketi + PushNotificationService
├── Gün 2: AndroidManifest + main.dart entegrasyon + test (local)
├── Gün 3: fiyat-push Edge Function doğrulama + FIREBASE_SERVER_KEY
├── Gün 4: run_all_bots.py push aktifleştirme + end-to-end test
└── Gün 5: Buffer + edge case (token yokken, izin reddedilince)

Hafta 2-3 — S4-F2: Kişisel Alarm
├── Gün 6: price_alerts SQL migration + PriceAlertService
├── Gün 7: PriceAlertDialog widget
├── Gün 8: station_bottom_sheet.dart entegrasyonu + sign-in guard
├── Gün 9: alert_checker.py + run_all_bots.py entegrasyonu
├── Gün 10: fiyat-push PERSONAL_PUSH action (Edge Function)
├── Gün 11: "Alarmlarım" listesi (ful_side_menu)
├── Gün 12: End-to-end test (alarm kur → fiyat düş → bildirim gel)
└── Gün 13: Buffer + release build test
```

---

## Human Actions (Geliştirici Yapmalı)

1. **Firebase Console:** FCM Server Key'i Supabase Secrets'a ekle (`FIREBASE_SERVER_KEY`)
2. **Supabase Dashboard:** `fiyat-push` Edge Function'a `PERSONAL_PUSH` action desteği ekle
3. **SQL Editor:** `database/sprint4_price_alerts.sql` çalıştır
4. **Gerçek cihaz testi:** Push bildirimleri emülatörde değil, gerçek cihazda test edilmeli

---

## Kritik Riskler

| Risk | Olasılık | Etki | Sprint Etkisi |
|------|---------|------|--------------|
| FCM Server Key kurulumu yapılmadan dev başlarsa push testi bloke olur | YÜKSEK | ORTA | Gün 3'te human action şart — öne al |
| firebase_messaging `^14.x` Dart 3.2.3 ile uyumlu mu? | ORTA | YÜKSEK | `flutter pub outdated` ile kontrol et |
| `fiyat-push` Edge Function PERSONAL_PUSH desteklemiyorsa S4-F2 kişisel push çalışmaz | ORTA | YÜKSEK | Sprint başında Edge Function kodu oku |

---

## Yeni Bağımlılıklar

| Paket | Sprint | Min Versiyon |
|-------|--------|-------------|
| `firebase_messaging` | Sprint 4 | ^14.7.10 |

---

*PRD S4 sonu. Implementasyona başlamadan önce "Human Actions" bölümündeki 4 adım tamamlanmalı.*
