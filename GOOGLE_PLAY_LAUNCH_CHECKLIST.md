# Fullet Google Play Launch Checklist

Son denetim: 2026-05-09

## Mevcut Teknik Durum

- Flutter release check geçti: backend health, ops report, backend unit test, `flutter analyze`, `flutter test`, release APK ve release AAB.
- Paket adı: `com.fullet.app`
- Sürüm: `1.0.1+2`
- Minimum SDK: `21`
- Target SDK: `35`
- Compile SDK: `36`
- Release APK: `C:\Users\yefec\Desktop\Fullet-1.0.1-build2-release.apk`
- Play'e yüklenecek ana dosya: `fullet_flutter\build\app\outputs\bundle\release\app-release.aab`
- Release APK imzası doğrulandı: v1 ve v2 signature geçerli.
- Backend canlı veri durumu temiz: 2223 aktif istasyon, 5422 aktif fiyat, pasif istasyonlar anon kullanıcıdan gizleniyor.

## Yayından Önce Bloklayan İşler

1. Google Maps API key kısıtlanmalı.
   - Android package: `com.fullet.app`
   - Local upload certificate SHA-1: `40:9B:C1:14:68:F0:BC:0F:C1:58:BE:4B:56:5D:8D:FD:20:5E:96:89`
   - Play App Signing açıldıktan sonra Google Play'in verdiği App signing certificate SHA-1 de ayrıca eklenmeli.
   - Kota ve bütçe uyarısı açılmalı. Sıfır maliyet hedefi için sürpriz fatura riski bırakılmamalı.

2. Gizlilik politikası public URL'ye alınmalı.
   - `PRIVACY_POLICY_DRAFT.md` taslak olarak hazır.
   - Play politikası PDF olmayan, herkese açık, aktif ve düzenlenemez bir URL istiyor.
   - Uygulama içinde de gizlilik politikasına erişim olmalı.

3. Data Safety formu doğru doldurulmalı.
   - Konum: yakındaki istasyonları bulmak ve mesafe hesaplamak için kullanılıyor.
   - Konum geçmişi/profil tutulmuyor.
   - Reklam ve analytics SDK yok.
   - Hesap sistemi yok.
   - Google Maps yol tarifi ve haber linkleri dış uygulama/site açabilir.

4. App icon değişmeli.
   - Şu an launcher icon Flutter varsayılan logosu.
   - Play Store'a çıkmadan önce Fullet'e ait sade, okunaklı ve markalı ikon yapılmalı.

5. Store listing hazırlanmalı.
   - Kısa açıklama, uzun açıklama, kategori, iletişim e-postası, ekran görüntüleri ve feature graphic hazırlanmalı.
   - Ekran görüntüleri gerçek cihazdan alınmalı: harita, istasyon detayı, sürüş modu, fiyat karşılaştırma.

6. Play test süreci seçilmeli.
   - İlk adım: Internal testing.
   - Eğer Google Play kişisel geliştirici hesabı 13 Kasım 2023'ten sonra açıldıysa production için kapalı testte en az 12 tester 14 gün kesintisiz opt-in kalmalı.

## Uyurken Çalışacak Bot Otomasyonu

- GitHub Actions workflow dosyası: `.github/workflows/otopilot.yml`
- Fiyat botları her gün Türkiye saatiyle yaklaşık 06:20, 12:20, 18:20 ve 00:20 çalışacak.
- Haber botu her gün Türkiye saatiyle yaklaşık 08:50 ve 20:50 çalışacak.
- İstasyon envanteri pazar günleri Türkiye saatiyle yaklaşık 04:40 çalışacak.
- GitHub repository secrets içinde şu değerler dolu olmalı:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY` veya service-role değerini taşıyan `SUPABASE_KEY`
  - `SUPABASE_ANON_KEY`
- En temiz kurulum: `SUPABASE_KEY` eski uyumluluk için kalabilir, ama service-role key ayrıca `SUPABASE_SERVICE_ROLE_KEY` adına da eklenmeli.
- `SUPABASE_ANON_KEY` olmazsa botlar service-role ile yazabilir, fakat RLS ve public okuma health check'i kırmızıya düşer.
- Workflow GitHub'a push edilmemişse veya Actions kapalıysa botlar otomatik çalışmaz.
- Workflow ilk kez GitHub'da açıldığında manuel `workflow_dispatch` ile `mode=prices`, `dry_run=1` denemesi yapılmalı; sonra `dry_run=0` canlı yazma testi yapılmalı.
- Haber tazeliği backend health check'e bağlı: en yeni haber 48 saati aşarsa sistem artık sağlıklı sayılmaz.

## Güçlü Ama Bloklamayan Teknik Borçlar

- Lokal Flutter SDK `3.16.5`; güncel paketlere çıkmak için Flutter SDK yükseltme planı yapılmalı.
- `flutter pub outdated` çıktısında güncel majör sürümü olan paketler var: `google_maps_flutter`, `geolocator`, `supabase_flutter`, `shared_preferences`.
- Bu yükseltme tester APK'yi engellemiyor ama uzun vadeli kalite hedefi için ayrı bir modernizasyon sprinti olmalı.

## Yayın Öncesi Komut

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release_check.ps1 -BuildApk -BuildAab
```

Bu komut temiz geçmeden Play'e dosya yüklenmemeli.

## Resmi Referanslar

- Target API: https://support.google.com/googleplay/android-developer/answer/11926878
- Play App Signing: https://support.google.com/googleplay/android-developer/answer/9842756
- Data Safety: https://support.google.com/googleplay/android-developer/answer/10787469
- User Data / Privacy Policy: https://support.google.com/googleplay/android-developer/answer/9888076
- Yeni kişisel hesap test şartları: https://support.google.com/googleplay/android-developer/answer/14151465
