# Fullet Google Play Hazırlık Notları

Son kontrol tarihi: 2026-05-07

## Teknik Durum

- Paket adı: `com.fullet.app`
- Minimum SDK: `21`
- Target SDK: `35`
- Release APK komutu: `flutter build apk --release`
- Play için tercih edilen paket: `flutter build appbundle --release`
- Yayın öncesi tam kontrol: `powershell -ExecutionPolicy Bypass -File .\scripts\release_check.ps1 -BuildAab`

## Yayın Öncesi Kırmızı Çizgiler

- `python scraper\backend_health_check.py` temiz bitmeden yayın yok.
- Canlı DB'de `database/production_hardening.sql`, `database/rls_policies.sql` ve gerekirse `database/live_public_schema_fix.sql` çalışmış olmalı.
- `verify_live_schema.sql` çıktısında `fiyatlar_veri_kaynagi_exists`, `push_tokens_provider_exists`, `istasyonlar_rls_enabled` ve `istasyonlar_anon_policy_filters_active` true dönmeli.
- Anon kullanıcı pasif istasyonları okuyamamalı. Health check bunu artık direkt fail eder.
- Fiyat ve istasyon verisi sadece resmi kaynaklardan gelmeli; sahte/tahmini fiyat canlıya yazılmayacak.

## Google Play Kontrolleri

- Google Play'in resmi hedef API dokümanı, 31 Ağustos 2025 itibarıyla yeni uygulama ve güncellemeler için Android 15/API 35 veya üstünü istiyor. Fullet şu an `targetSdkVersion 35` ile bu eşiği karşılıyor.
- Play App Signing kullanılmalı. Play Console'da App signing kurulumu tamamlanmadan AAB yükleme süreci bitmiş sayılmaz.
- Google Maps API key mutlaka Android paket adı `com.fullet.app` ve Play/App upload certificate SHA-1 değerleriyle kısıtlanmalı.
- Google Maps için kota ve bütçe uyarısı açılmalı. "0 maliyet" hedefi için fatura sürprizi bırakılmayacak.
- Data safety formu, uygulamanın gerçek veri kullanımına göre doldurulmalı.
- Privacy policy public, aktif, PDF olmayan, düzenlenemez bir URL'de yayınlanmalı ve uygulama içinden erişilebilir olmalı.
- Store görselleri gerçek cihaz ekran görüntülerinden seçilmeli.

## Data Safety Taslağı

Fullet hesap açtırmaz, kullanıcı profili oluşturmaz ve reklam/analytics SDK'sı kullanmaz.

- Konum: Yakındaki istasyonları bulmak, mesafe hesaplamak ve haritayı konumlandırmak için kullanılır. Yakın istasyon sorgusunda koordinat backend'e gönderilebilir. Konum geçmişi tutulmaz.
- Yerel tercihler: Seçili yakıt, garaj bilgisi, favoriler ve son bakılan istasyonlar cihazda saklanır.
- Ağ verisi: Resmi kaynaklardan toplanmış istasyon/fiyat/haber verileri Supabase üzerinden okunur.
- Harici açılışlar: Yol tarifi için Google Maps, haberler için dış tarayıcı/uygulama açılabilir.

## Resmi Referanslar

- Target API: https://support.google.com/googleplay/android-developer/answer/11926878
- Play App Signing: https://support.google.com/googleplay/android-developer/answer/9842756
- User Data / Privacy Policy: https://support.google.com/googleplay/android-developer/answer/9888076
- Data safety: https://support.google.com/googleplay/android-developer/answer/10787469
