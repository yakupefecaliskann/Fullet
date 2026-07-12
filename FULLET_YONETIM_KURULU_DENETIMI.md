# FULLET — BAĞIMSIZ YÖNETİM KURULU & YATIRIM DENETİMİ

**Hazırlayan:** Bağımsız board / yatırım komitesi rolünde değerlendirme
**Tarih:** 16 Haziran 2026
**Değerlendirilen materyal:** Flutter kod tabanı, Supabase şeması, scraper botları, Sprint 1–4 PRD'leri, Play Store launch dokümanları, gerçek uygulama ekranları, iş/gelir modeli, rakip ortamı, Türkiye akaryakıt fiyat regülasyonu.

> **Uyarı:** Bu rapor moral vermek için yazılmadı. Sana katılmak zorunda değilim ve katılmıyorum. Aşağıda fikrin temelinin neden çürük olabileceğini açıkça yazdım.

---

## ÖN TESPİT — EN ÖNEMLİ CÜMLE

Fullet teknik olarak iyi yapılmış, ürün olarak temiz, **ama yanlış bir pazarda doğru ürünü inşa ediyor.** Fullet'in çözmeye çalıştığı problem ("en ucuz benzini bul") Türkiye'de yapısal olarak **çözmeye değmeyecek kadar küçük bir problem.** Kendi ekranın bunu kanıtlıyor: istasyon detay haritandaki fiyatların neredeyse tamamı **63.98 TL** — biri 64.93. Senin "akıllı seçim" motorun bile tüm depo için **net 9.9 TL** tasarruf gösteriyor. Kimse 9.9 TL için uygulama indirmez, davranış değiştirmez ve **kesinlikle para ödemez.**

Bu rapor boyunca buna defalarca döneceğim, çünkü diğer her şey (kod kalitesi, tasarım, growth) bu tek gerçeğin yanında ikincil.

---

# A BÖLÜMÜ — ÜRÜN DENETİMİ

### Fullet hangi problemi çözüyor?
İddia: "Türkiye genelinde güncel akaryakıt fiyatlarını tek haritada gör, aracına göre sadece en ucuz değil en *mantıklı* (mesafe dahil toplam maliyet) istasyonu bul." Differentiator'ın `SmartStationService` — depo kapasitesi + tüketim + mesafe ile "toplam dolum maliyeti"ni hesaplaman. Bu fikir akıllıca.

### Bu problem gerçekten var mı? — **Büyük ölçüde HAYIR.**
İşte fikrin kalbine saplanan bıçak: **Türkiye'de istasyonlar arası fiyat farkı neredeyse yok.** Dağıtıcılar tavan/tavsiye fiyat belirliyor, EPDK 15 Mayıs 2024'ten itibaren aynı istasyonda aynı yakıtta tek fiyat zorunluluğu getirdi ve aynı il/ilçedeki markalar arası fark tipik olarak birkaç kuruş ile en fazla 1–1.5 TL. Senin ekranın da bunu gösteriyor (hepsi 63.98). Bir fiyat karşılaştırma uygulamasının var olma sebebi **fiyat dağılımıdır (price dispersion).** Türkiye akaryakıtında bu dağılım yok denecek kadar dar. Dağılım yoksa karşılaştırmanın değeri de yok. Bu, "düzeltilebilir bir eksik" değil, **regülasyondan gelen yapısal bir gerçek.**

### İnsanlar bu problem için para öder mi? — **HAYIR.**
Tasarruf 50 litrede ~5–10 TL bandında. Aylık ~2 dolum yapan bir kullanıcı için yıllık tasarruf bir kahve parası. Bunun için kimse Premium abonelik almaz. Senin kendi PRD'n bile monetizasyonu **100 üzerinden 5** veriyor (Sprint 3 sonunda umutla 18). Bu skoru sen verdin, ben değil.

### Ürün gereksiz karmaşık mı?
Hayır — aksine temiz. Onboarding net (3 kart), harita okunabilir, marka/yakıt filtresi mantıklı. Tek dosyada 2490 satırlık `modern_map_screen.dart` teknik borç sinyali ama kullanıcı bunu görmez.

### İlk kez gören biri 30 saniyede anlar mı?
Evet. Harita + fiyat baloncukları + filtre = anında anlaşılır. Bu artı. Ama "anlamak" ile "umursamak" farklı şeyler; anlıyor, sonra "zaten hepsi aynı fiyat" deyip siliyor.

### En güçlü özellikler
"Mesafe dahil toplam maliyet" akıllı seçim motoru (gerçek bir fikir), temiz harita UX'i, çoklu kaynaktan otomatik fiyat toplama altyapısı, otonom bot otomasyonu (günde 4 fiyat çekimi).

### En zayıf özellikler
Differentiator'ın (akıllı seçim) optimize ettiği şeyin kendisi (fiyat farkı) yok. Yani en güçlü özelliğin, var olmayan bir farkı optimize ediyor. Sıfır gelir modeli. Sadece Android. Hesap sistemi neredeyse yok.

### Gereksiz özellikler
"Garajım/araç ekleme" — şık ama tasarruf farkı bu kadar küçükken tüketim hesabının kullanıcıya kattığı net değer marjinal. Haber (news bot) — retention bahanesi, çekirdek değerle ilgisiz.

### Eksik özellikler
Gerçek bir **"neden bu uygulamayı açayım"** sebebi. Akaryakıt zammı *öncesi* uyarı (Sprint 4'te geliyor — doğru içgüdü, en güçlü kartın bu). iOS yok. Sadakat/indirme kartları entegrasyonu yok (markaların kendi indirimleri burada). Gerçek kişiselleştirme yok.

---

# B BÖLÜMÜ — PAZAR DENETİMİ

### Bu pazar büyüyor mu?
Araç sayısı ve yakıt tüketimi sabit/yavaş büyüyor; ama **"fiyat karşılaştırma" alt-pazarı yapısal olarak küçük** çünkü karşılaştırılacak fark yok. Akaryakıt harcaması dev bir pazar, ama "fiyat farkı bularak tasarruf" pazarı minik.

### Trend mi, kalıcı mı?
Akaryakıt kalıcı. Ama bu, "akaryakıt fiyat uygulaması" işinin de iyi olduğu anlamına gelmez — su da kalıcıdır, su faturası karşılaştırma uygulaması iyi bir iş değildir.

### Hedef kitle doğru mu?
Hedeflediğin "tasarruf arayan sürücü" gerçek bir kitle, ama bu kitleye sunduğun tasarruf gerçek değil. Yanlış vaad, doğru kitleye.

### Pazar büyüklüğü
TAM: Türkiye'deki ~30M+ sürücü. SAM: akıllı telefonla fiyat bakacak kesim, belki birkaç milyon. SOM (gerçekçi, gelir getiren): **neredeyse sıfır**, çünkü ödeme isteği yok. Reklamla bile 100K+ aktif kullanıcı olmadan anlamlı gelir çıkmaz ve o ölçeğe ulaşmak için sebep zayıf.

### En iyi ülke?
İronik biçimde **Türkiye değil.** Fiyat dağılımının yüksek olduğu, regülasyonun gevşek olduğu pazarlar: **ABD** (eyalet/istasyon farkı büyük — GasBuddy bu yüzden milyarlık oldu), Kanada, Avustralya, kısmen Almanya. Senin "toplam maliyet" motorun bu pazarlarda gerçek para kazandırır.

### En kötü ülke?
**Türkiye** ve benzeri tek-fiyat/tavan-fiyat rejimleri. Tam da kurduğun pazar.

### Hangi ülkelerde başarılı olur?
Fiyat serbestisi + yüksek dağılım olan yerler. Ama oralarda da GasBuddy/Waze/Google zaten oturmuş. Yani "doğru pazar = dolu pazar" ikilemi.

---

# C BÖLÜMÜ — RAKİP ANALİZİ

| Rakip | Güçlü yanı | Zayıf yanı | Fullet'in avantajı | Fullet'in dezavantajı |
|---|---|---|---|---|
| **GasAll** (100K+ indirme, 4.6★) | Kurulu kullanıcı tabanı, kapsam, marka bilinirliği | Eski UX, "toplam maliyet" mantığı zayıf | Daha temiz UX + akıllı seçim motoru | Sen daha hiç yayında değilsin; onlar 100K önde |
| **BenzinLitre** | Yakınlık + fiyat sıralaması, benzer konsept | Differentiation zayıf | UX/tasarım | Aynı fikir, önce geldiler |
| **Marka app'leri (Shell, Opet)** | Sadakat + gerçek indirim + ödeme entegrasyonu | Sadece kendi istasyonları | Çoklu marka karşılaştırma | Onlar gerçek para (indirim/puan) veriyor, sen 9.9 TL teorik tasarruf |
| **Google / Yandex Maps** | Herkesin telefonunda, fiyatı zaten gösteriyor, navigasyon dahil | Türkiye'de fiyat verisi sığ | Türkiye'ye özel daha derin fiyat | Dağıtım savaşını asla kazanamazsın |

### "Rakip olsaydım Fullet'i nasıl öldürürdüm?"
**Hiçbir şey yapmazdım.** Ciddiyim. Fullet'i benim öldürmeme gerek yok — **pazarın yapısı öldürüyor.** Fiyat farkı olmadığı için kullanıcı bir kez açar, "hepsi aynı" der, siler. Ama illa öldüreceksem en ucuz yol: GasAll'a senin "mesafe dahil toplam maliyet" özelliğini bir sprint'te eklerim ve 100K kullanıcıma push'larım. Bitti. Tek savunulabilir özelliğini bir haftada kopyalarım çünkü patentlenebilir/savunulabilir hiçbir tarafı yok.

---

# D BÖLÜMÜ — GELİR MODELİ

### İnsanlar neden öder? — Şu an **hiçbir sebep yok.**
Ödemek için "ödemezsem kaybederim" hissi gerekir. Tasarruf 9.9 TL iken bu his oluşmaz.

### İnsanlar neden ödemez?
Çünkü ücretsiz alternatif (Google Maps) cebinde, çünkü tasarruf önemsiz, çünkü akaryakıt zaten en sık şikayet edilen ama en az "optimize edilebilir" gider.

### Model değerlendirmesi
- **Freemium:** Mantıksız — premium'a koyacağın özellik (sınırsız alarm) ücretsiz versiyondan daha değerli değil.
- **Premium abonelik:** Mantıksız — değer/fiyat oranı negatif. Kimse benzin uygulamasına aylık ödemez.
- **Komisyon:** İlginç ama altyapı yok — istasyona müşteri yönlendirip CPA almak teorik olarak mümkün, ama markalar tek fiyatlı pazarda yönlendirme için ödemez.
- **Reklam:** Tek gerçekçi seçenek ama **sadece 100K+ DAU'da** anlamlı, ve o ölçeğe çıkacak çekim gücü yok. Düşük eCPM coğrafyası.
- **B2B / Veri:** **Tek ciddi yol.** Topladığın fiyat + istasyon + (anonim) talep verisi; akaryakıt dağıtıcıları, filo yönetim şirketleri, sigorta/analitik firmaları için değerli olabilir. Ürünü tüketiciye değil, **veriyi kuruma** satmak.

### En iyi gelir modeli
**Kısa cevap: Tüketici uygulamasının gelir modeli yok.** Eğer bir model seçeceksem **B2B veri/SaaS** (filo yakıt gideri optimizasyonu + fiyat verisi lisanslama). Tüketici tarafı ancak bir pazarlama/veri-toplama hunisi olarak anlam taşır, kâr merkezi olarak değil.

---

# E BÖLÜMÜ — GROWTH ANALİZİ

> Sert gerçek: Henüz **yayında bile değilsin** (Play launch checklist açık, internal testing aşaması). Growth konuşması teorik. Ürünü cilalamak yerine 10 kullanıcıyla "hepsi aynı fiyat" itirazını test etmeliydin.

- **İlk 100:** Arkadaş/çevre + birkaç Reddit (r/Turkey, r/otomobil) postu. Kolay, anlamsız sinyal.
- **İlk 1.000:** TikTok/Instagram Reels — "uygulama X TL kazandırdı" formatı. Ama tasarruf küçük olduğu için içerik inandırıcı olmaz. SEO ("bugün benzin fiyatı") burada en güçlü kanal.
- **İlk 10.000:** SEO + zam günü viralliği (zam haberleriyle eş zamanlı push/içerik). Tek gerçekçi ölçek motoru bu.
- **İlk 100.000:** Yalnızca bir influencer/PR dalgası + "zam alarmı" konumlandırmasıyla mümkün; mevcut değer önerisiyle ulaşılması düşük olasılık.

### Kanal sıralaması (ROI tahmini, bu ürün için)
1. **SEO** — "akaryakıt fiyatları / bugün benzin" yüksek hacimli arama. En yüksek ROI, ucuz, kalıcı. **ROI: Yüksek.**
2. **Zam günü içerik/PR** — haber döngüsüne bin. **ROI: Orta-Yüksek.**
3. **Reddit** — niş ama gerçek kullanıcı, ücretsiz. **ROI: Orta.**
4. **TikTok/Instagram** — tasarruf küçük olduğu için hook zayıf. **ROI: Düşük-Orta.**
5. **Influencer** — pahalı, dönüşüm belirsiz. **ROI: Düşük.**
6. **X** — Türkiye'de dağıtım zayıf. **ROI: Düşük.**
7. **Referral** — "9.9 TL" paylaşılası değil. **ROI: Düşük.**
8. **B2B** — ürün buysa farklı oyun; tüketici growth'u için alakasız. **ROI: (B2B pivotunda Yüksek).**

---

# F BÖLÜMÜ — YATIRIMCI GÖRÜŞÜ

**1 milyon dolarım olsa Fullet'in MEVCUT halinE yatırır mıydım? — HAYIR.**

**Sebepler:** (1) Çözdüğü problem regülasyon nedeniyle yapısal olarak küçük. (2) Gelir modeli yok ve görünür değil. (3) Savunulabilir bir hendek yok — tek özellik bir haftada kopyalanır. (4) Kurulu rakipler ve Google Maps karşısında dağıtım dezavantajı. (5) Solo kurucu, henüz yayında değil. (6) Pazar (Türkiye) düşük eCPM + düşük ödeme isteği.

**Riskler:** Scraper'lar marka siteleri değişince kırılır; yasal/ToS riski (resmi olmayan scraping); fiyat bayatlama → yanlış yönlendirme → güven kaybı; tek geliştirici bağımlılığı.

**Fırsatlar:** Topladığın temiz fiyat/istasyon veri kümesi gerçek bir varlık. "Toplam maliyet" motoru yüksek-dağılımlı pazarlarda veya B2B filo bağlamında değerli. Zam-alarmı konumlandırması zayıf bir tüketici kancası sağlayabilir.

**Yatırılabilirlik puanı: 22/100.** (Fikir + ekip yürütmesi iyi; pazar + model + hendek zayıf.)

---

# G BÖLÜMÜ — KURUCU ANALİZİ (Yaptığın muhtemel hatalar)

- **Zaman yönetimi:** En büyük hata. Aylarca Sprint 1–4, analytics, onboarding, push altyapısı inşa ettin — **ama "fiyatlar zaten aynı, kim umursar?" temel itirazını hiç test etmedin.** Bu tek soru, yazdığın bütün koddan önemliydi.
- **Ürün yönetimi:** Çözümle aşık oldun ("akıllı seçim motoru"), problemi doğrulamadın. PRD'lerin mühendislik olarak olgun, ürün-pazar uyumu olarak kör.
- **Pazarlama:** Henüz yayında değilken growth/feature planlıyorsun. Dağıtımı son adıma bıraktın — bu klasik teknik kurucu hatası.
- **Teknik:** Burada güçlüsün ama fazla güçlüsün — 2490 satırlık tek ekran, 7 ayrı kırılgan bot, sıfır gelirli bir ürün için aşırı mühendislik. Çabayı yanlış yere harcadın.
- **Finans:** Gelir modeli olmadan production altyapısı (Supabase, GitHub Actions, Maps API kotası) kuruyorsun. "Sıfır maliyet hedefi" iyi ama gelir sıfır olunca sürdürülebilirlik de sıfır.

---

# H BÖLÜMÜ — GERÇEKLİK TESTİ

### Batma ihtimali: **%88**
### Başarma (anlamlı, gelir getiren iş olma) ihtimali: **%12** — ve bu %12 büyük olasılıkla bir **pivot** sonrası gelir (B2B veri veya yüksek-dağılımlı pazar), mevcut tüketici-Türkiye kurgusuyla değil.

### En büyük 20 risk
1. Fiyat dağılımının olmaması (varoluşsal). 2. Gelir modeli yokluğu. 3. Google/Yandex Maps dağıtım ezici üstünlüğü. 4. GasAll'ın kurulu tabanı. 5. Scraper kırılganlığı. 6. Scraping yasal/ToS riski. 7. Bayat fiyat → yanlış yönlendirme → güven kaybı. 8. Tek geliştirici tükenmişliği. 9. iOS yokluğu (pazarın yarısı). 10. Maps API sürpriz faturası. 11. Düşük retention (açıp silme). 12. Premium dönüşümü ~%0. 13. Düşük eCPM coğrafyası. 14. Veri kapsamı sığ (2224 istasyon, Türkiye'de ~13.000+). 15. Marka app'lerinin gerçek indirimi. 16. Regülasyon değişimi (fiyat verisinin kapanması). 17. Supabase ölçek/maliyet. 18. App store onay/politika riski. 19. Differentiator'ın kopyalanabilirliği. 20. Kurucunun batık maliyet yanılgısıyla devam etmesi.

### En büyük 20 fırsat
1. Temiz fiyat/istasyon veri varlığı. 2. B2B veri lisanslama. 3. Filo yakıt-gideri SaaS'ı. 4. Yüksek-dağılımlı pazarlara (ABD/AU) genişleme. 5. Zam-öncesi alarm kancası. 6. SEO ile organik trafik. 7. Sigorta/analitik veri ortaklıkları. 8. EV şarj fiyatı/istasyonuna pivot (büyüyen, dağılımı olan pazar). 9. Akaryakıt + market + otopark "araç gideri" süper-app. 10. Marka sadakat entegrasyonu komisyonu. 11. "Toplam maliyet" motorunun lisanslanması. 12. Belediye/kamu veri ortaklığı. 13. White-label dağıtıcıya satış. 14. Anonim talep verisi (hangi bölgede ne arıyor). 15. Zam haberi medya/içerik markası. 16. Widget ile günlük etkileşim. 17. Topluluk (kullanıcı fiyat doğrulama). 18. Navigasyon ortaklığı. 19. Reklamveren olarak istasyon zincirleri. 20. Erken EV+yakıt hibrit konumlandırması.

### En kritik 10 hata
1. Problemi doğrulamadan ürün inşası. 2. Fiyat-dağılımı gerçeğini görmezden gelme. 3. Gelir modelini sona bırakma. 4. Dağıtımı sona bırakma. 5. Yüksek mühendislik / düşük validasyon. 6. Yanlış coğrafya (Türkiye). 7. Sadece Android. 8. Tek kişi her şeyi yapma. 9. Differentiator'ın savunulabilir olmaması. 10. Batık maliyetle devam riski.

### En kritik 10 karar
1. Devam mı, pivot mu, kapatma mı (60 gün içinde). 2. Tüketici mi, B2B mi. 3. Türkiye mi, yüksek-dağılım pazarı mı. 4. Akaryakıt mı, EV-şarj/araç-gideri mi. 5. Veriyi mi satacaksın, uygulamayı mı. 6. iOS yapılacak mı. 7. Solo mu, kurucu ortak mı. 8. Ne kadar daha para/zaman koyacaksın (stop-loss). 9. Scraping yerine resmi veri anlaşması. 10. Hangi tek metrik başarıyı tanımlıyor (ve onu kaç haftada görmen gerek).

---

# I BÖLÜMÜ — YOL HARİTASI

### 30 gün — GERÇEĞİ TEST ET (kod yazma)
Yayınla (internal/closed test yeter). 50–100 gerçek sürücüye ulaş. Tek soruyu cevapla: *"Fiyatlar zaten neredeyse aynıyken bu uygulama davranışını değiştiriyor mu?"* Retention (D1/D7) ve "istasyon değiştirdim mi" sinyaline bak. **Bu ay yeni özellik yok.** Veri konuşsun.

### 90 gün — KARAR NOKTASI
Eğer D7 retention < %10 ve kimse istasyon değiştirmiyorsa → **tüketici-Türkiye tezi öldü.** Pivot kararı ver: (a) B2B filo/veri, (b) EV-şarj fiyatı, (c) yüksek-dağılımlı pazar. Eğer beklenmedik şekilde tutuyorsa → zam-alarmını ve SEO'yu ölçekle.

### 6 ay — TEK BİR BAHSE ODAKLAN
Pivot ettiysen: ilk ödeyen B2B müşteriyi (1 filo/dağıtıcı pilotu) bul — gelir varlığını kanıtla. Tüketicide kaldıysan: 10.000 gerçek aktif kullanıcı + ilk reklam/ortaklık geliri. Net hedef: **birinin para ödediği tek bir kanıt.**

### 1 yıl — SÜRDÜRÜLEBİLİRLİK
Gelir > altyapı maliyeti (en azından başa baş). Tek bir net müşteri segmenti. Eğer hâlâ sıfır gelir ve düşük retention ise — **dürüstçe kapat, veri varlığını ve öğrendiklerini bir sonraki işe taşı.**

### 3 yıl — yalnızca pivot tutarsa
Türkiye'de akaryakıt+EV+araç-gideri veri/SaaS oyuncusu, ya da yüksek-dağılımlı pazarda tüketici uygulaması. Mevcut tezle 3 yıl konuşmak gerçekçi değil.

---

# J BÖLÜMÜ — SON KARAR

## "Fullet'e MEVCUT haliyle yatırım YAPMAM."

Pivot ya da yüksek-dağılımlı pazar olmadan, bu bir yatırım değil bir hobi projesidir — iyi yapılmış, ama yanlış pazarda.

| Kategori | Puan /100 |
|---|---|
| **Genel** | **28** |
| Ürün (zanaat olarak) | 64 |
| Ürün (pazar-uyumu olarak) | 18 |
| Growth | 25 |
| Pazar | 15 |
| Ekip (yürütme yeteneği) | 60 |
| Ekip (kapsam/tek kişi riski) | 30 |
| Savunulabilirlik (moat) | 12 |

### "Fullet benim şirketim olsaydı yarın sabah ne yapardım?"

Kod editörünü **açmazdım.** Bunun yerine:

1. **Sabah:** 20 gerçek sürücüyle (taksici, kurye, normal kullanıcı) tek tek konuşur, telefonlarındaki fiyat farkını birlikte açar, "bunun için ödeme yapar mısın / istasyon değiştirir misin?" diye sorardım. Yarım gün, sıfır kod, en değerli iş.

2. **Öğlen:** İki kolonlu bir sayfa yazardım — sol: "Türkiye'de akaryakıt fiyat farkı gerçekte kaç TL?" (kendi verimden gerçek dağılımı çıkar — istasyonlar arası medyan fark muhtemelen < 1 TL). Sağ: "Bu farkla kullanıcı davranışı değişir mi?" Bu tek slayt fikrin yaşayıp yaşamayacağını söyler.

3. **Öğleden sonra:** Stop-loss tanımlardım. "X hafta içinde D7 retention Y'ye ulaşmazsa pivot/kapatma." Batık maliyete (aylarca emek) duygusal bağ kurmayı reddederdim — yazılım çöp değil, **öğrenme;** ama yanlış pazarda inat etmek çöp.

4. **Akşam:** İki pivot hipotezini tek sayfada yazardım — **(a) B2B filo yakıt-gideri / veri lisanslama**, **(b) EV şarj fiyatı + istasyon** (büyüyen pazar, gerçek dağılım, regülasyon farklı). Hangisinin ilk ödeyen müşteriye 90 günde ulaştırabileceğini sorardım.

Yarın sabah yazacağın **en değerli kod sıfır satır.** Senin en büyük riskin teknik değil — zaten iyi mühendissin. En büyük riskin, harika inşa edilmiş bir gemiyi suyu olmayan bir göle indirmiş olman ve kürek çekmeye devam etmen.

---

### Kapanış
Fullet'in kodu, tasarımı ve disiplini bir kurucunun yürütme yeteneğini kanıtlıyor — bu senin gerçek varlığın, Fullet değil. Ama bu spesifik fikre, bu pazarda, bu modelle yatırım yapmam. Tezi çürüttüm; çürümediğini düşünüyorsan, beni 30 günlük retention verisiyle çürüt. Veri kazanır, ikimizin de fikri değil.

*— Bağımsız board / yatırım komitesi*
