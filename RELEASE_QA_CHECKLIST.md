# Fullet Release QA Checklist

Her yayın adayında bu liste bitmeden paket yüklenmez.

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

## Play Store

- App Bundle üretildi: `fullet_flutter\build\app\outputs\bundle\release\app-release.aab`
- Privacy policy URL hazır: `https://yakupefecaliskann.github.io/Fullet/privacy.html`
- Data safety formu uygulamadaki gerçek veri kullanımına göre dolduruldu.
- Google Maps API key paket adı + SHA-1 ile kısıtlandı.
- Store screenshots gerçek cihazdan alındı.
- Store açıklamasında fiyatların resmi kaynaklardan geldiği ve tahmini/sahte fiyat gösterilmediği yazıldı.
- Play icon kaynağı hazır: `fullet_flutter\assets\brand\fullet_play_icon_512.png`
