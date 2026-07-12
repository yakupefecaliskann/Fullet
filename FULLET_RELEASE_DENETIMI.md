# FULLET — RELEASE & TEKNİK DENETİM RAPORU

**Rol:** Release manager + teknik denetçi (ürün yöneticisi/yatırımcı DEĞİL)
**Tarih:** 16 Haziran 2026
**Amaç:** Bitir, yayınla, stabilize et, kritik riskleri kapat, **aylarca dokunmadan çalışabilir** bırak.
**İncelenen:** Flutter kodu, backend, 7 scraper botu, Supabase + pg_cron, GitHub Actions, Play Store hazırlığı.
**Kapsam kuralı:** Yeni özellik/pivot/iş modeli/sprint yok. Sadece mevcut ürünü güvenle yayına hazırlamak.

> **Tek cümlelik denetim sonucu:** Altyapı beklediğimden iyi mühendislik edilmiş (otomatik bayatlama, dayanıklı CI, sabit Python bağımlılıkları). Yayını bloklayan **bir gerçek güvenlik/maliyet riski** var (Maps API key) ve **bir mağaza-uyumu hatası** (Data Safety beyanı). "Aylarca dokunmama" hedefini tehdit eden iki sistemik tuzak var (GitHub cron 60 günde kapanır, Supabase free 7 günde uyur). Bunlar kapatılınca yayına hazır.

---

## A) YAYINI ENGELLEYEN KRİTİK PROBLEMLER

| # | Problem | Tip | Neden bloklar | Çözüm |
|---|---|---|---|---|
| **A1** | **Google Maps API key düz metin, AndroidManifest.xml satır 57'de ve git'e commit'lenmiş** (admin panel GitHub Pages'te canlı → repo büyük olasılıkla public → key hasat edilebilir) | Güvenlik + **Maliyet** | Kısıtsız key = sınırsız faturalandırma. Sen uygulamaya dokunmazken biri key'i kullanıp sana fatura çıkarabilir. Senin "0 maliyet" hedefinin tek gerçek tehdidi. | (1) Google Cloud'da key'i `com.fullet.app` paket adı + upload **ve** Play App Signing SHA-1 ile kısıtla. (2) Maps SDK'ya **günlük kota + bütçe uyarısı** koy. (3) Key git geçmişinde açıkta olduğu için **rotate et** (yeni key üret, eskisini sil). |
| **A2** | **Data Safety beyanı yanlış:** PLAY_STORE_READINESS.md "reklam/analytics SDK yok" diyor, ama `pubspec.yaml`'da `firebase_analytics` + `firebase_crashlytics` VAR | **Store reddi** | Google Data Safety formu ile gerçek SDK davranışı uyuşmazsa uygulama reddedilir veya sonradan askıya alınır. | Data Safety formunda Firebase Analytics (kullanım verisi) + Crashlytics (crash/diagnostik) topladığını dürüstçe beyan et. `google_sign_in`/`firebase_auth` fiilen kullanılıyorsa onu da; kullanılmıyorsa beyan etme ama bağımlılığı bırakman sorun değil. |
| **A3** | **Otomatik bayatlama (pg_cron) canlı DB'de kurulu mu teyit edilmemiş** | **Veri/güven riski** | `auto_price_staleness.sql` botlar kırılınca eski fiyatı "stale/unknown" yapan güvenlik ağın. Canlıda aktif değilse, bir bot öldüğünde kullanıcı **eski fiyatı güncel sanır** — yanlış yönlendirme + güven kaybı. Bu, maintenance-free olmanın bel kemiği. | SQL Editor'da `auto_price_staleness.sql`'i çalıştır, ardından `SELECT * FROM cron.job WHERE jobname LIKE 'fullet-%'` ile 4 job'ın `active=true` olduğunu doğrula. |
| **A4** | **GitHub secrets ve canlı şema doğrulanmamış** | Çökme/veri | Secret eksikse botlar yazamaz; şema eksikse health-check fail eder ve app boş veri gösterir. | `backend_health_check.py` canlıda temiz bitmeli; `verify_live_schema.sql` dört kontrolü `true`; GitHub'da `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_ANON_KEY` dolu. |
| **A5** | **Kapalı test başlatılmamış** | Store süreci | Kişisel hesap Kasım 2023 sonrasıysa production'dan önce 12 tester × 14 gün kesintisiz zorunlu. Başlatılmazsa yayın takvimi bloke. | Kapalı test track'ini **bu hafta** başlat; saat çalışsın. |

**Not (bloklamayan ama bilmen gereken):** `google-services.json` ve `firebase_options.dart` git'te. Bunlar normalde gizli sayılmaz (Firebase istemci tanımlayıcıları), client'a zaten gömülür. Yine de Firebase Console'da API key kısıtlamalarını (özellikle Maps/Geocoding) açık tut. `.env` doğru biçimde gitignore'da ve **izlenmiyor** — bu kısım temiz.

---

## B) YAYINDAN SONRA ÇÖZÜLEBİLECEK PROBLEMLER (kullanıcıyı bloklamaz)

| # | Konu | Tip | Neden ertelenebilir |
|---|---|---|---|
| B1 | `modern_map_screen.dart` 2490 satır, tek dosya | Refactor / teknik borç | Kullanıcı görmez, çalışıyor. Sadece *senin* gelecekteki bakımını zorlaştırır; aylarca dokunmayacaksan önceliği düşük. |
| B2 | İki ayrı bayatlama mekanizması: pg_cron (12h/48h) + `quarantine_old_prices.py` (72h) | Kod tekrarı | İşlevsel olarak çakışmıyorlar (pg_cron daha sıkı ve otoriter). Kafa karışıklığı yaratır ama zarar vermez. İleride `quarantine_old_prices.py`'yi emekliye ayırabilirsin. |
| B3 | Flutter bağımlılıkları caret (`^`) ile | Tekrarlanabilirlik | `pubspec.lock` commit'liyse sorun yok. Değilse, ileride `pub get` yeni sürüm çekip kırabilir — ama yayınlanmış APK'yı etkilemez. |
| B4 | `google_sign_in` / `firebase_auth` muhtemelen kullanılmayan bağımlılıklar | Kod temizliği / APK boyutu | Birkaç yüz KB. Reddi tetiklemez (Data Safety doğru doldurulduğu sürece). Sonra temizlenir. |
| B5 | Bot başarısızlığında bildirim yok (sessiz fail, aşağıda C'de) | Operasyonel görünürlük | Auto-staleness yanlış veriyi engellediği için *acil* değil; ama kapsamın sessizce daralmasını fark etmezsin. İsteğe bağlı iyileştirme. |
| B6 | Performans (marker clustering, büyük zoom-out) | Performans | Smoke-test'te kabul edilebilir çalışıyorsa ertelenebilir. |

---

## C) BAKIM YÜKÜNÜ AZALTMA PLANI

### Otomatik çalışan servisler (insan müdahalesi gerekmez)
- **Fiyat botları** — GitHub Actions, günde 4 kez (06:20/12:20/18:20/00:20 TR). Haber 2x, istasyon envanteri pazar.
- **Otomatik bayatlama** — Supabase pg_cron: fresh→stale (12h), stale→unknown (48h), eski istasyonları gizle (7g), push token temizliği (90g). **Bu, maintenance-free olmanın motoru.**
- **CI dayanıklılığı** — `FULLET_FAIL_ON_BOT_ERROR=0`: bir bot kırılsa diğerleri devam eder, run yeşil kalır. Health check + ops report her çalışmada koşar.
- **App tarafı** — istemci `price_status`'a saygı duyuyor: `isDisplayable => !isUnknown` (bilinmeyen gizlenir), `isTrustedForCalculations => isFresh` (akıllı seçim sadece taze fiyata güvenir). Yani güvenlik ağı uçtan uca çalışıyor. ✅

### Manuel müdahale gerektirenler
- **Kırılan bir scraper'ı onarmak** — marka sitesi HTML'i değişince ilgili bot patlar. Kaçınılmaz; tek gerçek tekrarlayan bakım kalemi.
- **GitHub cron'u canlı tutmak** (aşağıdaki kırılganlık #1).
- **Maps faturasını izlemek** — bütçe uyarısı kurulduktan sonra pasif.

### Kırılmaya en yatkın süreçler (önem sırasına göre)
1. **GitHub Actions zamanlanmış workflow'lar 60 gün repo aktivitesi olmazsa otomatik DEVRE DIŞI bırakılır.** → "Aylarca dokunmama" hedefinin **en büyük tehdidi.** ~60 gün sonra botlar durur → auto-staleness her şeyi "unknown" yapar → uygulama "fiyat bilinmiyor" gösterir (çökmez ama veri ölür).
2. **Supabase free-tier projeleri 7 gün hareketsizlikte uyutulur.** Botlar 4x/gün vurduğu için aktif kalır — ama #1 gerçekleşip botlar durursa ve app trafiği düşükse proje uyur → uygulama veriyi hiç okuyamaz (stale'den beter).
3. **Scraper'lar** — site değişimine kırılgan; auto-staleness yanlış veriyi engeller ama kapsamı sessizce daraltır.
4. **Maps key kotası** — kısıtsız/sınırsızsa kötüye kullanım/fatura riski.

### Minimum bakımla nasıl bırakılır
- **#1 için (en kritik):** İki seçenek — (a) Takvimine **8 haftada bir** repoya küçük bir commit atıp Actions'ı manuel "Enable" et (en basit, sıfır kod); ya da (b) bunu kabul et ve "~2 ay hands-off tavanı" olarak belgele. Otomatik bir "keep-warm" workflow bile 60 gün repo-aktivitesi kuralını aşmaz; gerçek çözüm periyodik commit'tir.
- **#2 için:** GitHub cron yaşadığı sürece Supabase de canlı kalır. #1 çözülürse #2 kendiliğinden çözülür. Ekstra güvence: Supabase'i ödeme planına almadan, projenin "pause" ayarını ve free-tier limitlerini (DB boyutu, ay sonu) bir kez kontrol et.
- **#3 için:** Beklenti yönet — bir markanın fiyatı günlerce "unknown" görünürse o botu onar. Auto-staleness sayesinde bu acil değil, kullanıcıya yanlış veri gitmez.
- **#4 için:** A1'deki kısıt + bütçe uyarısı kurulunca pasifleşir.

---

## D) YAYIN KARARI

# ➜ 2. Şu kritik işleri bitir, sonra yayınla.

Ürün ve altyapı yayına hazır; "hemen yayınla" demiyorum çünkü Maps key kısıtsız (gerçek maliyet/güvenlik riski) ve Data Safety beyanı yanlış (store reddi riski). "Erken" de değil — bunlar birkaç saatlik operasyon işi, haftalarca geliştirme değil. **Kapatılması gereken 5 iş:**

1. **A1** — Maps API key'i kısıtla + bütçe uyarısı + rotate et.
2. **A2** — Data Safety formunu Firebase Analytics + Crashlytics'i kapsayacak şekilde düzelt.
3. **A3** — `auto_price_staleness.sql`'i canlıda çalıştır + 4 pg_cron job'ının `active=true` olduğunu doğrula.
4. **A4** — `backend_health_check.py` canlıda temiz + `verify_live_schema.sql` dört kontrol `true` + GitHub secrets dolu.
5. **A5** — Kapalı test track'ini başlat (14 günlük saat).

Bu 5 iş bitince yayınla. Bunların hiçbiri "özellik" değil — hepsi release hijyeni.

---

## E) SON KONTROL LİSTESİ (≤20 madde)

**Güvenlik & Maliyet**
- [ ] 1. Maps API key'i paket adı + upload SHA-1 + Play App Signing SHA-1 ile kısıtla.
- [ ] 2. Maps SDK'ya günlük kota + bütçe uyarısı koy.
- [ ] 3. Git'te açığa çıkmış Maps key'ini rotate et (yeni key, eskisini sil).
- [ ] 4. Firebase Console'da Firebase API key kısıtlamalarını doğrula.
- [ ] 5. `.env`'in izlenmediğini son kez teyit et (temiz — yine de kontrol).

**Veri Sağlığı & Maintenance-Free**
- [ ] 6. `auto_price_staleness.sql` canlıda çalıştı; 4 pg_cron job `active=true`.
- [ ] 7. `backend_health_check.py` canlıda temiz bitiyor.
- [ ] 8. `verify_live_schema.sql`: dört kontrol `true`; anon pasif istasyon okuyamıyor.
- [ ] 9. GitHub secrets dolu: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`.
- [ ] 10. otopilot.yml'i `workflow_dispatch` ile elle bir kez koş; yeşil bitiyor + ops report mantıklı.
- [ ] 11. Supabase free-tier pause ayarı + limitleri (DB boyutu) bir kez kontrol edildi.
- [ ] 12. GitHub Actions 60-gün cron-kapanma kuralı not edildi; takvime "8 haftada bir commit + enable" hatırlatıcısı kondu.

**Uygulama Stabilitesi**
- [ ] 13. `flutter analyze` + `flutter test` temiz; release AAB üretiliyor (`release_check.ps1 -BuildAab`).
- [ ] 14. Gerçek cihazda RELEASE_QA_CHECKLIST smoke-test'i baştan sona geçti.
- [ ] 15. Crashlytics canlı veri alıyor; konum izni reddinde + ağ hatasında app çökmüyor, anlaşılır mesaj veriyor.
- [ ] 16. `pubspec.lock` repoya commit'li (tekrarlanabilir build).

**Play Store**
- [ ] 17. Data Safety formu Firebase Analytics + Crashlytics'i doğru beyan ediyor.
- [ ] 18. Privacy policy URL canlı + app içinden erişilebilir; store listing + gerçek cihaz görselleri + tek feature graphic hazır.
- [ ] 19. Kapalı test başlatıldı: 12 tester × 14 gün opt-in sürüyor.
- [ ] 20. Production'a **staged rollout** (%20-50) ile yükle; ilk crash dalgasını izleyip kademeli %100.

---

### Bu liste tamamlandığında:
**"Fullet artık yayınlanabilir ve kurucu uzun süre dokunmasa da çalışabilir"** demeye hazırsın — **tek istisna ve dürüst sınır:** GitHub Actions cron'u 60 günde bir repoya commit atılmazsa devre dışı kalır. Yani gerçek hands-off tavanın **~2 ay**; her 2 ayda bir 2 dakikalık "commit + workflow enable" dışında uygulama kendi kendine ayakta kalır. Bunu kabul edersen ürün bitmiştir. Amaç büyütmek değildi; **bitirmekti — ve bitti.**
