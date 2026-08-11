# Fullet Release QA Checklist

Her yayın adayında bu liste bitmeden paket yüklenmez.

> **1.0.3+6 koşusu (4 Ağustos 2026):** Backend ve Flutter blokları geçti
> (`dart analyze` temiz, 45/45 test). Cihaz smoke test'i **Infinix X6528B /
> Android 13** üzerinde release derlemesiyle koşuldu; crash yok. Edge-to-edge
> bloğu **kısmen** doğrulandı — cihaz API 33 olduğu için Android 15/16'nın
> zorunlu edge-to-edge davranışı tetiklenmedi. Bir sonraki koşuda API 35+ bir
> cihaz kullanılmalı.

## Backend

- `python scraper\backend_health_check.py`
- `python scraper\ops_report.py`
- `python -m unittest test_backend_utils test_aytemiz_bot`
- Botlar DB yazmadan test edilecekse: `powershell -ExecutionPolicy Bypass -File .\scripts\release_check.ps1 -RunBotsDryRun`
- Canlıya yazmadan önce `FULLET_DRY_RUN=1` ile bot çıktıları kontrol edilmeli.
- Canlı yazma sadece `FULLET_ALLOW_DB_WRITE=1` ile bilinçli açılmalı.

## Flutter

- `flutter analyze`
- `flutter test`
- `flutter build apk --release`
- Play adayı için: `flutter build appbundle --release`

## Cihaz Smoke Test

- Uygulama ilk açılışta haritayı ve yakıt seçiciyi gösteriyor.
- Benzin, Motorin, LPG geçişleri markerları yeniliyor.
- Harita uzaklaştırılınca clusterlar sadece istasyon sayısı gösteriyor.
- Yakınlaşınca tek istasyon markerlarında gerçek fiyat görünüyor.
- Arama açılıyor, sonuç listesi geliyor, istasyon seçince panel açılıyor.
- Favori yıldızı çalışıyor; favori/son bakılan istasyon aramada öne geliyor.
- Filtre paneli açılıyor; marka ve sıralama seçimleri haritaya yansıyor.
- Konum izni reddedilirse anlaşılır bilgi gösteriliyor.
- Bağlantı/veri hatasında tekrar dene akışı gösteriliyor.
- Yol tarifi butonu harici harita uygulamasını açıyor.

## Edge-to-Edge (Android 15+ / API 36 — targetSdk 36'dan beri zorunlu)

Bu blok **gerçek cihazda** koşulmalı; emülatör jest çubuğu yüksekliğini her zaman
doğru raporlamıyor. Hem **jest navigasyonu** hem **3 düğmeli navigasyon** ile bakılmalı.

- İstasyon detay paneli açıkken en alttaki buton (Yol tarifi) navigasyon çubuğunun
  ÜSTÜNDE; çubuk paneli kesmiyor.
- Panelin bulanık zemini çubuğun arkasına kadar uzanıyor (altta harita görünen boşluk yok).
- Yan menü sonuna kadar kaydırıldığında son öğe çubuğun altında kalmıyor.
- Sağdaki FAB yığını (tema, konumum, sürüş) ve sol alttaki lejant çubukla çakışmıyor.
- Üst arama çubuğu durum çubuğunun altında kalmıyor.
- Klavye açılıp kapandığında panel yukarı zıplamıyor / çubuğun altına kaymıyor.
- Koyu ve açık temada durum çubuğu ikonları okunabilir (zemine göre kontrast doğru).

## Play Store

- App Bundle üretildi: `fullet_flutter\build\app\outputs\bundle\release\app-release.aab`
- AAB **upload keystore** ile imzalandı — doğrulama komutu:
  `powershell -ExecutionPolicy Bypass -File .\scripts\verify_aab_signature.ps1`
  (script `[OK]` demeden paket yüklenmez; bkz. `GOOGLE_PLAY_LAUNCH_CHECKLIST.md` §2.1)
- Play Console'da **upload key reset** onaylandı (yeni anahtara geçiş, 4 Ağu 2026).
- Privacy policy URL hazır: `https://yakupefecaliskann.github.io/Fullet/privacy.html`
- Data safety formu uygulamadaki gerçek veri kullanımına göre dolduruldu.
- Google Maps API key paket adı + SHA-1 ile kısıtlandı.
- Store screenshots gerçek cihazdan alındı.
- Store açıklamasında fiyatların resmi kaynaklardan geldiği ve tahmini/sahte fiyat gösterilmediği yazıldı.
- Play icon kaynağı hazır: `fullet_flutter\assets\brand\fullet_play_icon_512.png`

## Yayın SONRASI doğrulama (yandan yükleme ile YAPILAMAZ)

> **Neden ayrı bir blok:** 11 Ağustos 2026'da Play'den kuran herkeste harita boş
> açıldı, çünkü Maps API anahtarında app signing SHA-1 eksikti. Yayın öncesi tüm
> cihaz testi yandan yüklemeyle yapılmıştı ve o yolda hata **yapısal olarak
> görünmez** — sideload edilen APK senin upload anahtarınla imzalıdır, Play'den
> gelen ise Google'ın app signing anahtarıyla. Detay: `GOOGLE_PLAY_LAUNCH_CHECKLIST.md` §2.2

Yayın canlıya çıktıktan sonra, uygulamayı cihazdan **tamamen kaldır** ve
**Play Store'dan indir**; ardından:

- Harita karoları geliyor (boş/gri/beyaz değil) — *app signing SHA-1 kontrolü*
- Google ile giriş çalışıyor — *OAuth istemcisi app signing SHA-1'iyle eşleşiyor mu*
- İstasyon ve fiyat verisi yükleniyor
- Yol tarifi butonu harici harita uygulamasını açıyor
