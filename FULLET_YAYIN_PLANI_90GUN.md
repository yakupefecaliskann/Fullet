# FULLET — YAYIN PLANI & 90 GÜN (Solo Geliştirici / Mevcut Vizyon)

**Çerçeve:** VC yok, unicorn yok, pivot yok. Vizyon sabit: *"Yakıt fiyatlarını karşılaştıran ve kullanıcıya en mantıklı istasyonu bulduran uygulama."* Amaç: bitir, yayınla, stabilize et, gerçek kullanıcıya ver, sonra yeni projeye geç. Aşağısı buna göre.

> **Tek cümlelik acımasız tespit:** Sen geride değilsin — **bitmiş bir ürünün üstüne kapsam ekleyerek yayını geciktiriyorsun.** Düşmanın eksik özellik değil, Sprint 4. 1.0.2 zaten release build alıyor. Sorun "hazır mı?" değil, "ne zaman durup yükleyeceksin?"

---

## 12 SORU — NET CEVAPLAR

**1) Mevcut haliyle yayınlanmaya hazır mı?**
**Evet, ürün olarak hazır.** v1.0.2+3 release APK/AAB üretiyor, backend hardened (2224 istasyon, 5425 fiyat), QA ve health-check betiklerin mevcut. Kalan işler **ürün değil, mağaza/operasyon işi** (API key kısıtı, privacy URL, Data Safety formu, store listing, kapalı test). Yani "kod bitmedi" değil, "yayın süreci başlatılmadı" durumundasın.

**2) Yayın öncesi MUTLAKA yapılması gerekenler?**
Kırmızı çizgiler (kendi dokümanlarından + Google kuralı):
- `backend_health_check.py` temiz bitmeli; `verify_live_schema.sql` dört kontrolü `true` dönmeli; anon kullanıcı pasif istasyonları okuyamamalı.
- `release_check.ps1 -BuildAab` ile `flutter analyze` + `flutter test` + release AAB temiz.
- **Google Maps API key'i** paket adı + SHA-1 ile kısıtla + kota/bütçe uyarısı aç (sürpriz fatura = tek gerçek mali riskin).
- Privacy policy URL canlı + uygulama içinden erişilebilir.
- Data Safety formu doğru (hesap yok, reklam/analitik SDK yok — ama Firebase Analytics/Crashlytics VAR, formda bunu doğru beyan et).
- **Kapalı test track'ini BUGÜN başlat** (aşağıdaki #5'e bak — bu senin gerçek zaman kısıtın).

**3) Güzel olur ama ertelenebilir?**
Widget, "yolum üzerinde" modu, istasyon yorumları, tasarruf geçmişi, fiyat trend grafiğinin gelişmiş hali, hesap/login sistemi, iOS. Hepsi v1.1+. Yayını bunların hiçbiri bloklamamalı.

**4) Kesinlikle v1'e YETİŞTİRİLMEMELİ?**
- **Sprint 4'ün tamamı: FCM push + kişisel fiyat alarmı.** Kodda yok, PRD'si 13 günlük iş + 4 "human action" + Edge Function riski. Bu v1'i 3 hafta geciktirir ve yayın için gerekli değil. **Yayından SONRA, gerçek kullanıcı varken yap.**
- Hesap sistemi, ödeme, çoklu cihaz senkronu — hiçbiri v1 değil.

**5) "Tamam artık yayınla" ne zaman?**
RELEASE_QA_CHECKLIST'teki cihaz smoke-test'i tek gerçek cihazda baştan sona geçtiğinde ve mağaza kırmızı çizgileri tamamlandığında. **Mükemmellik değil, "çökmüyor + temel akış çalışıyor" eşiği.** Pratikte: Crashlytics'te kritik crash yok + harita/yakıt geçişi/arama/yol tarifi çalışıyor → yükle. **Önemli kısıt:** kişisel geliştirici hesabın 13 Kasım 2023 sonrası açıldıysa, production'dan önce **12 tester × 14 gün kesintisiz kapalı test** zorunlu. Yani "yayınla" demek = **kapalı testi bugün başlat**; 14 günlük saat senin gerçek darboğazın, kod değil.

**6) Solo dev olarak nerede gereksiz zaman harcıyorsun?**
- **Sprint 4 PRD'si yazmak** (yayınlanmamış ürüne özellik planlamak).
- **7 ayrı marka botu + scraper'ı sonsuz cilalamak** — çalışıyor, yeter; kırılınca düzelt.
- **2490 satırlık `modern_map_screen.dart`'ı refactor etmek** — kullanıcı görmez, v1'i bloklamaz.
- **Aşırı backend hardening / observability** (admin panel zaten var). Yeterince sağlam.
- **Feature graphic'in 5. varyantını üretmek.** Birini seç, devam et.
Bunların hepsi "ilerliyormuş gibi hissettiren ama yayına yaklaştırmayan" işler.

**7) Yayından sonra ilk 30 gün nasıl davranmalısın?**
Yeni özellik yazma. Üç şey yap: (a) **Crashlytics + ANR'leri günlük izle**, sadece crash/blocker düzelt. (b) **Fiyat tazeliğini izle** — bot kırılırsa veri bayatlar, bu tek ölümcül hatan. (c) **Gerçek kullanım verisine bak** (zaten Firebase Analytics kurulu): kaç kişi açıyor, istasyona tıklıyor, yol tarifi alıyor, ertesi gün geri dönüyor mu. Tepki ver, inşa etme.

**8) İlk 100 kullanıcıdan hangi veriyi topla?**
Zaten logladığın event'lerden: **D1/D7 retention**, `station_tapped → directions_requested` dönüşümü (gerçek niyet sinyali bu), `garage_vehicle_set` oranı (akıllı mod kullanılıyor mu), oturum başına süre, en çok bakılan il/marka. Niteliksel: 5-10 kullanıcıya tek soru — *"Bu yüzden gerçekten istasyon değiştirdin mi?"* Cevap "hayır"sa, bunu erkenden bilmek senin için bir zafer.

**9) İlk 1000 kullanıcıya en basit plan?**
Tek kanal, ücretsiz, yüksek niyet: **SEO + zam günü.** "Bugün benzin/motorin fiyatı [il]" araması çok yüksek hacimli — uygulamanı bu aramalara bağla (basit landing/içerik) ve zam haberi çıktığı gün Reddit (r/Turkey, r/otomobil) + ilgili Facebook/şehir grupları + Ekşi'de organik paylaş. Influencer/reklam yok. Para harcama; emek harca. 1000 kullanıcı için fazlası gerekmez.

**10) Başarısız olsa bile bu projeden ne kazanırsın?**
Çok şey, ve bu önemli: **uçtan uca tek başına bir ürünü production'a çıkarma deneyimi** — Flutter + Supabase + PostGIS + scraping + CI/CD (GitHub Actions) + Play Store yayın süreci + analytics. Bu, yazdığın koddan daha değerli; bir sonraki projende haftalar kazandırır. Ayrıca: çalışan bir veri-toplama altyapısı, portfolyoda gösterilebilir canlı bir uygulama, ve "ne zaman durulur" disiplinini öğrenmek. Başarısız bir launch ≠ kayıp; **yayınlamadan bırakmak** = kayıp.

**11) Kapatma/dondurma kriterleri?**
Net eşikler koy, duyguyla karar verme: Yayından **60 gün sonra** (a) D7 retention < %8 ise, (b) `directions_requested` dönüşümü çok düşük (kimse aksiyon almıyor) ise, (c) organik kurulum aylık tek hanede kalıyorsa, ve (d) sen artık üstünde çalışmaktan keyif almıyorsan → **dondur.** Dondurmak = botları çalışır bırak, yeni geliştirme durdur, yeni projeye geç. Bu bir başarısızlık değil, kaynak yönetimi. Uygulamayı silmen gerekmez; sadece üstüne daha fazla zaman gömmeyi bırak.

**12) Senin yerinde olsam şu an ne yapardım?**
Sprint 4 PRD'sini kapatır, bir cihazda QA smoke-test'i baştan sona koşar, kapalı test track'ini **bugün** başlatır (14 günlük saati hemen çalıştırmak için), 14 gün dolarken store listing + Data Safety + API key kısıtını hallederdim. Sonra production'a yükler, ilk 30 günü yalnızca stabilizasyon + izleme yapar, 60. günde yukarıdaki kapatma kriterlerine bakıp **devam mı, dondur mu** kararını verirdim. Yeni özellik = sadece gerçek kullanıcı verisi talep ederse.

---

## ✅ BU HAFTA YAPILACAKLAR

- [ ] Sprint 4'ü (push + fiyat alarmı) resmen **v1.1'e ertele.** PRD'yi kapat, dokunma.
- [ ] `powershell .\scripts\release_check.ps1 -BuildAab` koş → `flutter analyze`, `flutter test`, release AAB temiz mi?
- [ ] `python scraper\backend_health_check.py` + `ops_report.py` temiz bitiyor mu?
- [ ] `verify_live_schema.sql`: dört kontrol `true` mü? Anon pasif istasyon okuyamıyor mu?
- [ ] **Gerçek cihazda** RELEASE_QA_CHECKLIST smoke-test'ini baştan sona koş; bulduğun blocker crash'leri düzelt (sadece onları).
- [ ] Google Cloud'da Maps API key'i `com.fullet.app` + SHA-1 ile kısıtla, **kota + bütçe uyarısı aç.**
- [ ] Privacy policy URL'sinin canlı + app içinden açıldığını doğrula.
- [ ] Play Console'da **kapalı test (closed testing) track'ini oluştur ve AAB'yi yükle** → 12 tester davet et. (14 günlük saat bu hafta başlamalı.)

## 🚀 YAYIN GÜNÜ YAPILACAKLAR

- [ ] 12 tester × 14 gün kesintisiz opt-in tamamlandı mı (hesap Kasım 2023 sonrasıysa zorunlu).
- [ ] Store listing hazır: kısa + uzun açıklama, kategori, iletişim e-postası, gerçek cihaz ekran görüntüleri, feature graphic (tek varyant — seç ve bitir).
- [ ] Açıklamada: "fiyatlar resmi kaynaklardan, tahmini/sahte fiyat gösterilmez" cümlesi.
- [ ] Data Safety formu doğru (Firebase Analytics/Crashlytics kullanımını dürüst beyan et).
- [ ] Play App Signing kurulumu tamamlandı; Google'ın verdiği App signing SHA-1'i Maps key'e de ekledin.
- [ ] Crashlytics canlı ve veri alıyor.
- [ ] Production track'e **staged rollout** (%20-50) ile yükle — %100 değil; ilk crash dalgasını sınırla.
- [ ] Botların GitHub Actions cron'larının canlıda çalıştığını teyit et (fiyat 4x/gün).

## 📅 İLK 30 GÜN YAPILACAKLAR

- [ ] **Günlük:** Crashlytics + ANR kontrol → sadece crash/blocker hotfix. Yeni özellik YOK.
- [ ] **Günlük:** Fiyat tazeliği kontrol (admin panel) — bot kırılırsa veri bayatlar = en ölümcül hata.
- [ ] **Haftalık:** Firebase Analytics'te D1/D7 retention, `station_tapped→directions_requested` dönüşümü, `garage_vehicle_set` oranını not et.
- [ ] 5-10 gerçek kullanıcıya ulaş, tek soru: *"Bu yüzden gerçekten istasyon değiştirdin mi?"*
- [ ] SEO/zam-günü dağıtımını başlat (Reddit + şehir grupları + Ekşi, organik). Para harcama.
- [ ] Staged rollout'u kademeli %100'e çıkar (crash oranı düşükse).
- [ ] **30. gün:** Toplanan veriyle 60. gün kapatma kriterlerini gözden geçir; "devam / dondur" kararına bir hafta kala hazırlan.

---

### Kapanış (acımasız ama kapsam içinde)
Mevcut vizyon sabitken yapabileceğin en sağlıklı şey: **bu ay yayınla, bir ay stabilize et, veriye bak, kararını ver.** Bu uygulamayı "bitirilecek" değil, "yayınlanıp öğrenilecek" bir şey olarak gör. Tek gerçek başarısızlık senaryosu, aylarca daha cilalayıp hiç yayınlamamak. Kodun hazır — eksik olan tek şey **durma kararı.** Onu bu hafta ver.
