# FULLET — KARAR PROTOKOLÜ (Veriyle Doğrulanmış)

**Tarih:** 2 Ağustos 2026
**Bağlam:** Çıkış röportajları yapılamıyor (organik kullanıcılar, kimlik yok).
**Yöntem:** Kanaat değil, canlı Supabase verisi. Tüm sayılar `xhkvlwecsacfjpbtyqcc` üzerinde koşulmuş sorgulardan.

---

## 0. ÖNCE ŞUNU NETLEŞTİRELİM: ÇIKIŞ RÖPORTAJLARI KAYIP DEĞİL

Çıkış röportajının cevaplayacağı soru şuydu: *"İnsanlar neden yol tarifi almadan siliyor?"*
Beklenen cevap: *"Çünkü fiyatlar zaten aynıydı."*

Bu cevabı artık **15 kişinin izleniminden değil, 7.247 fiyat kaydından** biliyoruz. Nitel
araştırma, nicel veriyle ölçülemeyen şeyler için yapılır. Bu soru ölçülebilirdi ve ölçüldü.

Ayrıca pratik gerçek: **günlük aktif kullanıcı sayısı 1.** Bu hacimde hiçbir anket, hiçbir
uygulama içi soru istatistiksel anlam üretmez. Çıkış röportajını "telafi etmeye" çalışmak
kaybedilmiş zaman olur. Telafi etmiyoruz; gerek yok.

---

## 1. BULGU: FİYAT FARKI YOK — KENDİ VERİNİZLE KANITLANDI

Board denetiminin (16 Haziran) tüm tezi tek bir iddiaya dayanıyordu: *"Türkiye'de istasyonlar
arası fiyat dağılımı yok."* Bu iddia artık **doğrulandı.**

**İlçe bazında, aynı yakıt, aynı gün, ≥2 marka (66 karşılaştırılabilir grup):**

| Ölçüm | Değer |
|---|---|
| Medyan fark | **0,05 TL/litre** |
| 75. persentil | 0,06 TL |
| 90. persentil | 0,07 TL |
| Farkın < 0,25 TL olduğu grup oranı | **%97,0** |
| Farkın ≥ 1 TL olduğu grup oranı | %3,0 |

**Marka ortalamaları (ülke geneli, taze fiyatlar):**

| Yakıt | En ucuz marka | En pahalı marka | Toplam yelpaze |
|---|---|---|---|
| Kurşunsuz 95 | BP 68,17 | TotalEnergies 68,56 | **0,39 TL** |
| Motorin | Shell 81,75 | TotalEnergies 82,51 | **0,76 TL** |

### Bunun anlamı
Kullanıcının kendi ilçesinde yakalayabileceği medyan tasarruf: **litrede 5 kuruş.**
50 litrelik depoda: **~3 TL.**

Board raporu "9,9 TL" demişti ve bunu iyimser bulmuştu. Gerçek sayı onun **üçte biri.**

> Not: 7.247 kaydın tamamında il bazında medyan fark 3,49 TL çıkıyor — ama bu **sahte bir
> sinyal.** Bayat (`stale`/`unknown`) fiyatlar analize girdiğinde, farkın kaynağı coğrafya
> değil **zaman** oluyor (3 hafta önceki fiyat ile bugünkü fiyat zam nedeniyle farklı).
> Sadece taze fiyatlarla ölçüldüğünde medyan 0,06 TL'ye düşüyor. Bu ayrımı yapmayan her
> analiz yanıltıcıdır.

---

## 2. BULGU: SHELL LPG FİYATLARI SİSTEMATİK OLARAK YANLIŞ (AKTİF HATA)

`scraper/shell_bot.py:128`:

```python
"LPG": _price_at(cols, 12) or _price_at(cols, 10),
```

Sabit kolon indeksi + `or` fallback. Sonuç:

| Marka | LPG ortalaması | Kayıt |
|---|---|---|
| Petrol Ofisi | 31,28 TL | 76 |
| BP | 31,35 TL | 35 |
| **Shell** | **37,74 TL** | **860** |

Shell, diğer tüm markalardan **6,4 TL (%20) yukarıda** — hem de her istasyonda birebir aynı
değerle (İstanbul'un tamamı 38,51). Bu istasyon bazlı dağılım değil, **kolon eşleme hatası.**

**Hatanın LPG'ye özel olduğu doğrulandı:** Shell'in Motorin (81,75) ve Kurşunsuz 95 (68,52)
değerleri diğer 6 markayla kusursuz uyumlu. Yani site değişmemiş, sorun sadece o indekste.
`min` değerinin 30,86 çıkması da bunu doğruluyor: satır kısa olduğunda fallback (indeks 10)
devreye giriyor ve **doğru** fiyatı okuyor.

### Neden önemli
LPG'ye dönüşmüş sürücü, yoldaki **en fiyat-hassas segment** — arabasını zaten tasarruf için
dönüştürmüş, litre fiyatını ezbere bilir. Uygulamayı açıyor, Shell'i ezberindeki fiyatın
6,5 TL üstünde görüyor. 50 litrelik dolumda **325 TL'lik hata.** Vardığı sonuç: "bu uygulama
yanlış." Elinizdeki az sayıda kullanıcının en motive olanına, apaçık hatalı veri gösterildi.

### Acı ironi
Bu hata düzeltilince fiyat dağılımı **daha da düzleşir.** Yani düzeltme, iş modelini
kurtarmaz — tam tersine tabutun son çivisidir. Yine de düzeltilmeli (bkz. Adım 1).

---

## 3. BULGU: BOTLAR SESSİZCE BAŞARISIZ — PANEL YEŞİL, VERİ ÖLÜ

`bot_runs` tablosunda son 2 koşunun **tamamı `status = success`, `exit_code = 0`.**
Gerçek durum:

| Marka | Taze fiyat oranı | Son yazım |
|---|---|---|
| TotalEnergies | %50,0 | 2 Ağu |
| Shell | %23,9 | 2 Ağu |
| BP | %19,0 | 2 Ağu |
| **Opet** | **%0,0** | 1 Ağu |
| **Petrol Ofisi** | **%0,0** | 1 Ağu |
| **Türkiye Petrolleri** | **%0,0** | 1 Ağu |
| **Aytemiz** | **%0,0** | 1 Ağu |

7 markanın 4'ünde **tek bir taze fiyat yok.** Bu botlar bugün 10:51'de "başarıyla" koştu ve
hiçbir şey yazmadı. Toplamda 7.247 fiyatın yalnızca **%20,6'sı taze**; %79'u bayat veya
bilinmiyor.

Board raporunun 7 numaralı riski ("bayat fiyat → yanlış yönlendirme → güven kaybı") teorik
değil, **şu anda aktif.** Ve gözlem sisteminiz bunu göstermiyor — çünkü "0 kayıt yazdım"
durumu `success` sayılıyor.

---

## 4. BULGU: KULLANICI VERİSİ SANDIĞINIZDAN BÜYÜK VE DAHA NET

15 değil — `app_heartbeats` tablosunda **99 kurulum** var. Ayrımı yapmak şart:

| Kohort | Kurulum | D1 dönen | D7 dönen | D7 oranı |
|---|---|---|---|---|
| Mayıs (kapalı test / çevre) | 20 | 10 | 7 | %35 |
| **Organik (21 Tem sonrası)** | **28** | **5** | **1** | **%3,6** |
| Toplam | 99 | 20 | 10 | %10,1 |

Mayıs kohortu arkadaş/tester — o %35 gerçek sinyal değil. **Gerçek sayı organik kohortun
%3,6'sı.** Ortalama heartbeat sayısı 1–3; heartbeat 15 dakikada bir atıldığına göre bu,
kullanıcının uygulamada **toplam 15–45 dakika** geçirip bir daha dönmediği anlamına geliyor.

### Kendi eşiğiniz
`FULLET_YAYIN_PLANI_90GUN.md` madde 11'de dondurma kriterini siz yazmıştınız:

> *"Yayından 60 gün sonra D7 retention < %8 ise → dondur."*

**Şu an %3,6.** Kendi koyduğunuz eşik, kendi verinizle karşılandı. Karar için daha fazla veri
beklemeye gerek yok — veri geldi.

---

## 5. KARAR

Tüketici tarafında **Türkiye akaryakıt fiyat karşılaştırma tezi ölmüştür.** Bu bir pazarlama,
UX veya dağıtım sorunu değil. Ürün, var olmayan bir farkı optimize ediyor: medyan 5 kuruş.
Hiçbir özellik, hiçbir kanal, hiçbir tasarım bunu değiştiremez.

**Ama bu "her şey çöp" demek değil.** Analizin kendisi bir sonraki hamleyi de gösteriyor:

> **Dağılım nerede varsa ürün oradadır.**
> Akaryakıtta dağılım regülasyonla sıfırlanmış. Elektrikli araç şarjında sıfırlanmamış.

Altyapınızın tamamı — PostGIS harita, istasyon envanteri, fiyat scraping, 4x/gün cron,
"mesafe dahil toplam maliyet" motoru — yakıt cinsinden bağımsız. `CANONICAL_FUELS` içinde
`"Elektrik"` zaten tanımlı ve **boş.** Aynı makineyi dağılımın gerçekten olduğu bir pazara
çevirmek, sıfırdan başlamak değil; hedef değiştirmektir.

Bu bir umut değil, **test edilecek bir hipotez** — ve 2 haftada, kod yazmadan test edilebilir.

---

## 6. ADIM ADIM PLAN

### ADIM 1 — Veriyi dürüst hale getir (bu hafta, ~3 saat)

Bu adım ürünü kurtarmak için değil. **Elinizde her senaryoda kalacak tek varlık veri setidir**
(B2B, portfolyo, EV pivotu — hepsinde). %20 sistematik hatalı veri hiçbir senaryoda işe
yaramaz. Ayrıca şu anda canlı kullanıcılara yanlış fiyat gösteriyorsunuz; bu, strateji ne
olursa olsun düzeltilmesi gereken bir doğruluk borcudur.

- [ ] **Shell LPG kolonunu düzelt.** `shell_bot.py:128`. Doğru indeks canlı sayfadan teyit
      edilmeli — sabit sayı yerine **başlık metnine göre kolon bulma** yaz (`normalization.py`
      zaten "lpg"/"otogaz" metnini tanıyor, o mantığı kolon seçimine bağla).
- [ ] **Çapraz doğrulama kapısı ekle.** Bir markanın bir yakıttaki medyanı, diğer markaların
      medyanından %10'dan fazla saparsa → yazma, `system_alerts`'a alarm düş. Bu tek kural
      bu hatayı en başta yakalardı.
- [ ] **Sessiz başarısızlığı bitir.** Bot 0 kayıt yazdıysa `success` dönmesin (`bot_runs`'a
      `records_written` kolonu ekle; 0 ise `status='empty'` + alarm).
- [ ] **Opet / PO / TP / Aytemiz'in neden hiç taze fiyat yazmadığını bul.** 4 bot "başarılı"
      koşup hiçbir şey yazmıyor — parse mi kırık, diff mantığı mı atlıyor?

**Neden ilk sıra:** Bundan sonraki her adım (özellikle Adım 3'ün EV ölçümü) bu veri hattının
doğru çalışmasına bağlı. Kirli aletle ölçüm yapılmaz.

---

### ADIM 2 — Bulguyu yayınla, uygulamayı değil (1 gün)

Elinizde Türkiye'de kimsenin gerçek veriyle yayınlamadığı bir cevap var:
**"Türkiye'de akaryakıt fiyat farkı gerçekte kaç TL?"** — 2.617 istasyon, 80 il, 7.247 fiyat,
cevap: 5 kuruş.

- [ ] Tek sayfa: grafik + yöntem + ham sayılar. Reklam yok, uygulama indirme çağrısı yok.
- [ ] Ekşi / r/Turkey / r/otomobil / şehir grupları — organik, para harcamadan.
- [ ] Ölçülecek tek şey: **kimse bu veriyi umursuyor mu?**

**Neden:** Board raporunun en yüksek ROI'li kanalı SEO'ydu ("bugün benzin fiyatı" yüksek
hacimli arama). Bu, uygulamanın değil **verinin** talebi olup olmadığını test eden en ucuz
deney. Bir gün maliyeti var, ve iki sonucu da bilgilendirici: ilgi varsa veri bir varlık,
yoksa bu yol da kapanır ve bunu kesin olarak bilirsiniz.

**Kill kriteri:** 2 hafta içinde 500'ün altında ziyaret → veri-içerik yolu da kapalı, bir
daha açma.

---

### ADIM 3 — EV şarj hipotezini ölç (2 hafta, ~1 gün gerçek iş)

**Bu, planın stratejik kalbi.** Akaryakıt tezini öldüren aynı ölçümü, EV şarjında tekrarlayın.

- [ ] 3–4 şarj ağının (ZES, Eşarj, Trugo, Voltrun) **halka açık fiyat listelerini** çek. Tam
      bot yazma — tek seferlik manuel/yarı-otomatik çekim yeter.
- [ ] Adım 1'deki **aynı dağılım sorgusunu** koş: aynı il, aynı gün, ağlar arası medyan fark.
- [ ] Karşılaştır: akaryakıtta 0,06 TL/litre. EV'de kaç TL/kWh?

**Karar kuralı — şimdiden bağlayıcı:**

| Sonuç | Anlamı | Aksiyon |
|---|---|---|
| Medyan fark **> %10** | Dağılım gerçek, karşılaştırmanın değeri var | Fullet'i EV şarj haritasına çevir. Altyapı hazır, "toplam maliyet" motoru burada gerçekten para kazandırır. |
| Medyan fark **%3–10** | Sınırda | Sadece Adım 2 ilgi gördüyse devam et |
| Medyan fark **< %3** | Akaryakıtla aynı hikâye | **Dondur.** Pivot yok. |

**Neden bu pivot, diğerleri değil:**
- *B2B veri lisanslama:* Board'un önerisiydi ama satacağınız veri "bütün fiyatlar aynı"
  diyor. Alıcı (dağıtıcılar) zaten kendi fiyatını biliyor. Solo kurucu için de uzun,
  ilişki-yoğun bir satış. **Öncelik değil.**
- *Yüksek dağılımlı pazar (ABD/AU):* Dağılım var ama GasBuddy 20 yıllık ve orada dağıtım
  savaşını kazanma şansınız sıfır.
- *EV şarj:* Dağılım muhtemelen var, pazar büyüyor, regülasyon farklı, Türkiye'de kimse
  oturmuş değil, **ve altyapınızın %90'ı aynen çalışır.** Tek gerçek aday bu.

---

### ADIM 4 — 30. günde bağlayıcı karar (1 Eylül 2026)

Duyguyla değil, yukarıdaki üç adımın çıktısıyla:

- **EV dağılımı > %10 VEYA Adım 2 ciddi ilgi gördü** → Tek bahse odaklan, 90 gün ver, yeni
  bir stop-loss yaz.
- **İkisi de olmadı** → **Dondur.** Bu şu demek: botlar çalışmaya devam etsin (maliyeti
  ~sıfır, veri birikmeye devam etsin), uygulama mağazada kalsın, **yeni geliştirme dursun.**
  Silme, kapatma, utanma yok. Kaynak yönetimi bu.

---

## 7. NE YAPMAYACAKSINIZ (bu kadar önemli)

- ❌ Yeni özellik yok. Sprint 5 yok. Fiyat alarmını tamamlama yok.
- ❌ iOS yok.
- ❌ `modern_map_screen.dart` refactor yok.
- ❌ Uygulama içi anket yok — günde 1 aktif kullanıcıyla anlamsız.
- ❌ Çıkış röportajını telafi etme çabası yok — soru zaten cevaplandı.
- ❌ Reklam/influencer'a para yok.

Adım 1'deki veri düzeltmesi **tek istisnadır** ve o da yeni özellik değil, doğruluk borcudur.

---

## 8. KAPANIŞ

31 Temmuz'da kod defterini kapattınız — doğru karar. Bugün öğrendiğimiz şey, o defteri
yeniden açmanız gerekmediği. Fullet teknik olarak başarılı, ticari olarak yanlış pazarda.
Bunu artık tahminle değil **kendi verinizle** biliyorsunuz: medyan 5 kuruş.

Bu projeden çıkan gerçek varlık uygulama değil: uçtan uca çalışan bir veri toplama makinesi
ve onu okumayı bilen bir kurucu. Bugünkü analizin tamamı — dağılım ölçümü, kolon hatasının
tespiti, sessiz bot arızası, kohort ayrımı — o makinenin üstünde 20 dakikada yapıldı. O
yetenek bir sonraki işe aynen taşınır.

Sıradaki soru "Fullet'i nasıl kurtarırız?" değil.
**"Bu makineyi dağılımın gerçekten olduğu bir yere çevirebilir miyiz?"** — ve bunun cevabı
Adım 3'te, iki hafta içinde, kod yazmadan çıkacak.
