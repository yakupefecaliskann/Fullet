# FULLET — GO-TO-MARKET VE BÜYÜME STRATEJİSİ

**Belge sahibi:** Büyüme & Pazarlama (CMO / Head of Growth)
**Sürüm:** 1.0 · **Tarih:** 7 Ağustos 2026
**Uygulama:** Fullet — `com.fullet.app` · Google Play'de **canlı**
**Bütçe varsayımı:** **0 TL ücretli medya.** Tüm plan organik, topluluk ve ürün içi
kanallar üzerine kurulmuştur.
**Kapsam dışı:** Kaynak kod, mimari, teknik borç. Bu belge yalnızca iş geliştirme,
kullanıcı edinme, elde tutma ve gelir modeli üzerinedir.

---

## İÇİNDEKİLER

1. [Yönetici Özeti](#1-yönetici-özeti)
2. [Pazar, Rekabet ve Savunulabilir Fark](#2-pazar-rekabet-ve-savunulabilir-fark)
3. [Hedef Kitle ve Personalar](#3-hedef-kitle-ve-personalar)
4. [Konumlandırma ve Mesaj Mimarisi](#4-konumlandırma-ve-mesaj-mimarisi)
5. [ASO — Google Play Optimizasyonu](#5-aso--google-play-optimizasyonu)
6. [Sosyal Medya ve Viral Kanallar](#6-sosyal-medya-ve-viral-kanallar)
7. [Topluluk ve Gerilla Pazarlama](#7-topluluk-ve-gerilla-pazarlama)
8. [Retention ve Etkileşim](#8-retention-ve-etkileşim)
9. [Monetizasyon Yol Haritası](#9-monetizasyon-yol-haritası)
10. [30-60-90 Günlük Eylem Planı](#10-30-60-90-günlük-eylem-planı)
11. [KPI Panosu ve Ölçüm Mimarisi](#11-kpi-panosu-ve-ölçüm-mimarisi)
12. [Riskler ve Önlemler](#12-riskler-ve-önlemler)
13. [Ekler — Kullanıma Hazır Metinler](#13-ekler--kullanıma-hazır-metinler)

---

## 1. YÖNETİCİ ÖZETİ

### 1.1 Tek cümlelik konumlandırma

> **Fullet, sana en ucuz istasyonu değil, cebinde en çok para bırakan istasyonu
> gösteren akaryakıt haritasıdır.**

Bu cümle rastgele seçilmiş bir slogan değil, ürünün gerçek teknik farkının doğrudan
tercümesidir. Fullet'in `smart_station_service` katmanı bir istasyonu puanlarken üç
değişkeni birlikte hesaplar: litre fiyatı, kullanıcının aracının tank kapasitesi ve
tüketimi, ve o istasyona gitmenin yakıt maliyeti. Piyasadaki fiyat listesi
uygulamalarının tamamı yalnızca birinci değişkeni gösterir. **"3 km öteye gidip
litrede 40 kuruş kazanmak aslında zarardır"** içgörüsü, Fullet'in tek başına
sahiplenebileceği bir konumdur.

### 1.2 Stratejinin üç ayağı

| Ayak | Ne yapıyoruz | Neden bu |
|------|--------------|----------|
| **1. Veri otoritesi ol** | Günde 4× toplanan fiyat verisini bir *içerik makinesine* çevir; zam/indirim haberini ilk ve en doğru veren hesap ol | Sıfır bütçeyle ölçeklenen tek şey içeriktir ve elimizde kimsede olmayan ham veri var |
| **2. Acıyı en çok hisseden kitleyle başla** | Kurye, moto-kurye, taksi/ticari sürücü, şehirlerarası sürücü — yakıt gideri gelirinin %20-40'ı olan kitle | Yüksek kullanım sıklığı + doğal ağız-kulak yayılımı + topluluk yoğunluğu |
| **3. Dürüstlüğü ürün özelliği olarak sat** | "Doğrulayamadığımız fiyatı göstermiyoruz" ilkesini pazarlamanın merkezine koy | Kategorinin en büyük kullanıcı şikâyeti "fiyatlar yanlış/eski". Bu bizim en güçlü karşı-konumlandırmamız |

### 1.3 Sıfır bütçe ne demek, ne demek değil

**Değiştirdiği şey:** Google UAC, Meta Ads, ücretli influencer ve PR ajansı planlardan
çıkar. CPI ile ölçeklenen bir edinme modeli kurulamaz.

**Değiştirmediği şey:** Hedef büyüklük. Türkiye'de 30 milyondan fazla trafiğe kayıtlı
kara taşıtı var; kategori araması yüksek hacimli ve mevsimsellikten bağımsız. Sıfır
bütçeyle yüz binlerce kuruluma ulaşan uygulamalar, bunu **tek bir kanalda otorite
olarak** başarır. Bizim kanalımız: *zam anını sahiplenen fiyat verisi içeriği*.

**Bunun bedeli:** Zaman ve tutarlılık. Ücretli medya parayla satın alınan hızdır;
organik büyüme haftalık disiplinle satın alınan hızdır. Aşağıdaki 13 haftalık plan,
tek kişilik bir ekibin haftada ~8-10 saat ayırabileceği varsayımıyla kalibre edilmiştir.

### 1.4 90 günlük kuzey yıldızı

| Metrik | 30 gün | 60 gün | 90 gün |
|--------|--------|--------|--------|
| Kuzey yıldızı: **haftalık yol tarifi alan kullanıcı** (WAU-intent) | ölçüm zemini kurulur, taban belirlenir | tabanın 3×'i | tabanın 8-10×'u |
| Toplam kurulum (kümülatif) | +%50 | +%200 | +%500 |
| D1 / D7 retention | ölçülür | D1 ≥ %30 | D1 ≥ %35, D7 ≥ %15 |
| Play puanı | ≥ 4,3 | ≥ 4,4 (≥30 yorum) | ≥ 4,5 (≥100 yorum) |
| Organik marka araması ("fullet") | — | ölçülebilir hale gelir | toplam trafiğin ≥%15'i |

> **Not:** Mutlak kurulum sayısı yerine çarpan hedefi kullanılmıştır; çünkü mevcut taban
> Play Console'dan okunmalıdır. İlk hafta işi budur (bkz. §10, W1).

---

## 2. PAZAR, REKABET VE SAVUNULABİLİR FARK

### 2.1 Pazarın yapısı

Türkiye akaryakıt fiyat bilgisi pazarı üç katmanda çalışır:

1. **Marka kendi uygulaması** (Shell, Opet, PO, TotalEnergies): Yalnızca kendi
   istasyonunu gösterir. Karşılaştırma yapmaz — yapması da ticari olarak imkânsızdır.
   *Bu bizim rakibimiz değil, varlık sebebimizdir.*
2. **Fiyat listesi siteleri ve genel uygulamalar:** İl bazında liste verir, harita ve
   konum zayıftır, veri tazeliği belirsizdir, reklam yoğunluğu yüksektir.
3. **Navigasyon uygulamaları** (Google Maps, Yandex): İstasyonu gösterir, fiyatı
   Türkiye'de güvenilir biçimde göstermez.

**Boşluk:** *Konum + karşılaştırma + fiyat güvenilirliği + araç bazlı maliyet
hesabı* dördünü aynı anda yapan yok.

### 2.2 Rekabet karnesi

| Yetenek | Marka uygulamaları | Fiyat listesi uygulamaları | Navigasyon | **Fullet** |
|---|---|---|---|---|
| Çok markalı karşılaştırma | ✗ | ✓ | kısmi | ✓ |
| Konum bazlı harita + kümeleme | kısmi | zayıf | ✓ | ✓ |
| **Araç bazlı gerçek maliyet hesabı** | ✗ | ✗ | ✗ | **✓ (tek)** |
| **Fiyat kapsam şeffaflığı** (il ilanı / istasyon doğrulaması) | — | ✗ | ✗ | **✓ (tek)** |
| Doğrulanamayan fiyatı gizleme | — | ✗ | — | **✓** |
| Fiyat geçmişi / trend | ✗ | kısmi | ✗ | ✓ |
| Sürüş modu (canlı GPS) | ✗ | ✗ | ✓ | ✓ |
| Reklamsız deneyim | ✓ | ✗ | ✓ | ✓ (bugün) |

> **Aksiyon:** Bu tablo bir pazarlama varlığıdır. §6'daki içerik planında "karşılaştırma
> görseli" olarak, §7'de forum girişlerinde kanıt olarak, §13'te Play açıklamasında
> özet halinde kullanılacaktır. Rakip isimleri **belgede ve içerikte açıkça
> zikredilmez** — kategori kıyaslaması yapılır, marka karalama yapılmaz. Bu hem
> Play politikası hem itibar açısından doğru olandır.

### 2.3 Üç savunulabilir hendek (moat)

1. **Kendi veri altyapımız.** Fiyat, hazır bir API'den satın alınmıyor; 7 marka için
   ayrı botlarla, Shell'de headless tarayıcıyla il/ilçe gezilerek toplanıyor. Bunu
   kopyalamak bir hafta sonu işi değil, aylarca sürecek bir mühendislik yatırımıdır.
2. **Fiyat kapsamı şeffaflığı.** "Ankara geneli ilan fiyatı" ile "İstasyondan
   doğrulandı" ayrımını yapan tek uygulama biziz. Bu, taklit edilebilir ama taklit
   edildiğinde rakibin *geçmiş verisinin güvenilmezliğini itiraf etmesi* gerekir.
3. **Akıllı skor + garaj verisi.** Kullanıcı aracını bir kez tanımladığında ürün
   kişiselleşir; bu, geçiş maliyeti (switching cost) yaratır.

---

## 3. HEDEF KİTLE VE PERSONALAR

Dört segment, **öncelik sırasıyla** aşağıdadır. Sıfır bütçeyle aynı anda dört segmente
gidilmez; W1-W6 arası **yalnızca P1 ve P2**'ye odaklanılır.

### P1 — "Mehmet, Moto-Kurye" (İlk hedef · En yüksek öncelik)

| | |
|---|---|
| **Profil** | 24-38 yaş, büyükşehir, motosikletli yemek/kargo kuryesi veya esnaf kuryesi. Günde 120-250 km. |
| **Acı** | Yakıt, net gelirinin %20-35'i. Haftada 4-6 kez depo dolduruyor. Litrede 50 kuruş fark, ayda gerçek bir yemek parası. |
| **Tetikleyici an** | Vardiya başı, depo çeyreğe düştüğünde, zam duyulduğu akşam |
| **Fullet'te gördüğü değer** | Yakınındaki en mantıklı istasyon + zam öncesi uyarı + favori istasyon takibi |
| **Nerede bulunur** | Facebook kurye grupları, WhatsApp/Telegram vardiya grupları, kurye toplanma noktaları (yemek platformu bekleme alanları), Instagram kurye hesapları |
| **Ona söylenecek cümle** | *"Zam gecesi haberi ilk sende olsun. Ayda bir depo bedavaya gelsin."* |
| **Neden birinci sırada** | Kullanım sıklığı en yüksek segment (retention motoru), fiziksel olarak kümelenmiş (dağıtım kolay), birbirine yoğun tavsiye eder (viral katsayı) |

### P2 — "Ayşe, Günlük Şehir İçi Sürücü" (Hacim segmenti)

| | |
|---|---|
| **Profil** | 28-50 yaş, işe arabayla gidiyor, haftada 150-300 km, 10-15 günde bir depo |
| **Acı** | Fiyatın nereden bakılacağını bilmiyor; "hangisi ucuz" sorusuna cevabı yok. Zam haberini sosyal medyadan duyuyor ama nereye gideceğini bilmiyor. |
| **Tetikleyici an** | **Zam haberi** (en güçlü tetikleyici), yakıt lambası yandığında, uzun yola çıkmadan önce |
| **Fullet'te gördüğü değer** | Zam öncesi "bu gece depo doldur" uyarısı; yakınındaki fiyat farkı |
| **Nerede bulunur** | X (Twitter) zam gündemi, Instagram Reels, Google Play arama, Ekşi Sözlük, Reddit |
| **Ona söylenecek cümle** | *"Bu gece yarısı motorine zam geliyor. Depon boşsa, bu 300 TL demek."* |
| **Neden ikinci** | En büyük hacim burada; ama edinme maliyeti (organik olarak: içerik emeği) en yüksek. P1'de kurulan güven, P2'ye içerikle yayılır. |

### P3 — "Hakan, Ticari Araç / Şehirlerarası Sürücü" (Derinlik segmenti)

| | |
|---|---|
| **Profil** | Kamyonet/panelvan/TIR, küçük filo sahibi ya da sürücüsü. Aylık 3.000-15.000 km. |
| **Acı** | Rota üzerinde nerede dolduracağı ciddi bir para kararı. İl geçişlerinde fiyat farkı yüksek. Şu an bunu tecrübeyle çözüyor. |
| **Tetikleyici an** | Yola çıkmadan önce planlama; il sınırına yaklaşırken |
| **Fullet'te gördüğü değer** | Motorin odaklı harita, geniş envanter (6.000+ istasyon), il bazlı fiyat farkı görünürlüğü |
| **Nerede bulunur** | Nakliyeci/şoför Facebook grupları, sözlük, YouTube kamyon/tır kanalları yorumları, nakliye forumları |
| **Ona söylenecek cümle** | *"İstanbul-Ankara arası nerede doldurursan kârlısın? Harita söylüyor."* |
| **Neden üçüncü** | Yüksek değerli ama küçük ve ulaşması zor kitle. W7+ ele alınır; ileride B2B gelir modelinin kapısıdır. |

### P4 — "Emre, LPG'li / Ekonomi Sürücüsü" (Niş, yüksek dönüşüm)

| | |
|---|---|
| **Profil** | LPG dönüşümlü araç, fiyat duyarlılığı maksimum, forum ve grup kullanıcısı |
| **Acı** | LPG fiyatı istasyon bazında en çok değişkenlik gösteren yakıt; listeler çoğunlukla LPG'yi eksik veriyor |
| **Tetikleyici an** | Her depo (LPG dolum sıklığı yüksek) |
| **Fullet'te gördüğü değer** | LPG yakıt tipi filtresi + gerçek maliyet hesabı |
| **Nerede bulunur** | LPG'li araç Facebook grupları, otomobil forumları (marka alt forumları), YouTube |
| **Ona söylenecek cümle** | *"LPG fiyatını gerçekten takip eden harita."* |
| **Neden dördüncü** | Küçük ama en yüksek dönüşüm oranlı kitle. Düşük emekle iyi getiri — W5'te tek bir kampanyayla girilir. |

### 3.1 Segment × Değer teklifi matrisi

| Ürün özelliği | P1 Kurye | P2 Günlük | P3 Ticari | P4 LPG |
|---|:---:|:---:|:---:|:---:|
| Akıllı skor (araç bazlı maliyet) | ★★★ | ★★ | ★★★ | ★★ |
| Zam/indirim uyarısı | ★★★ | ★★★ | ★★ | ★★★ |
| Yakındaki istasyon haritası | ★★★ | ★★★ | ★★ | ★★ |
| Fiyat kapsam şeffaflığı | ★★ | ★★ | ★★★ | ★★★ |
| Sürüş modu | ★★★ | ★ | ★★★ | ★ |
| Favoriler | ★★★ | ★★ | ★★ | ★★★ |
| Fiyat trendi (sparkline) | ★★ | ★★ | ★★★ | ★★ |
| Geniş envanter (6.000+) | ★★ | ★★ | ★★★ | ★★ |

**Okuma:** İletişimde her segmente ★★★ olan 2 özelliği söyle, gerisini söyleme.
Herkese her şeyi anlatan mesaj, hiç kimseye bir şey anlatmaz.

---

## 4. KONUMLANDIRMA VE MESAJ MİMARİSİ

### 4.1 Konumlandırma ifadesi (dahili — dışarı çıkmaz)

> Yakıt gideri bütçesinde ciddi yer tutan Türkiye'deki sürücüler için Fullet,
> yalnızca litre fiyatını değil aracının tüketimini ve istasyona gitme maliyetini de
> hesaba katarak **gerçekten kârlı olan istasyonu** gösteren akaryakıt haritasıdır.
> Fiyat listesi veren uygulamaların aksine Fullet, doğrulayamadığı fiyatı hiç
> göstermez ve gösterdiği her fiyatın kaynağını açıkça yazar.

### 4.2 Mesaj hiyerarşisi

| Katman | Mesaj | Nerede kullanılır |
|---|---|---|
| **Ana iddia** | "En ucuz değil, **en mantıklı**." | Store başlığı, bio'lar, her içeriğin kapanışı |
| **Destek 1** | Aracını tanıt, hesabı sana göre yapalım (garaj + akıllı skor) | Onboarding, Reels, ASO açıklama |
| **Destek 2** | Doğrulayamadığımız fiyatı göstermiyoruz | Yorum yanıtları, forum girişleri, kriz anları |
| **Destek 3** | 6.000+ istasyon, 7 marka, günde 4 kez güncelleme | Store açıklaması, basın, karşılaştırma görseli |
| **Kanıt** | Fiyat kapsamı etiketi, fiyat geçmişi, bot çalışma sıklığı | Ekran görüntüleri, "nasıl çalışıyor" içeriği |

### 4.3 Kaçınılacak mesajlar (yasak liste)

| Deme | Neden | Bunun yerine |
|---|---|---|
| "Türkiye'nin en iyi/1 numaralı yakıt uygulaması" | Kanıtlanamaz, Play politikası riskli, güven kırar | "Aracına göre hesap yapan tek harita" |
| "Yakıtta %X tasarruf garantisi" | Garanti edilemez, şikâyet üretir | "Bu depoda ne kadar fark ettiğini göster" |
| Rakip marka adıyla kıyaslama | Marka riski + platform politikası | Kategori kıyaslaması ("fiyat listesi uygulamaları") |
| "Anlık, canlı fiyat" | Veri günde 4× toplanıyor; abartı ilk şikâyette geri teper | "Günde 4 kez güncellenen, kaynağı yazılı fiyat" |
| Petrol şirketlerini hedef alan siyasi/polemik dil | Marka itibarı + hukuki temas riski | Nötr, veri odaklı ton |

**Genel kural:** Fullet'in tonu **serinkanlı, veri odaklı, abartısız ve faydacıdır.**
Zam gündeminde herkes bağırırken sakin ve doğru olan hesap, otorite olur.

---

## 5. ASO — GOOGLE PLAY OPTİMİZASYONU

ASO, sıfır bütçeli bir uygulamanın **tek ölçeklenebilir edinme kanalıdır** ve
maliyeti yalnızca emektir. Öncelik sırası: **Başlık > Kısa açıklama > İkon >
İlk 3 ekran görüntüsü > Uzun açıklama > Yorum hacmi/puan.**

### 5.1 Anahtar kelime havuzu

Google Play'de Türkiye pazarı için hedeflenecek kelimeler üç kümede toplanır.
Hacim tahminleri **Play Console → Store performance → Search terms** ve
Google Keyword Planner ile W1'de doğrulanmalıdır — aşağıdaki sınıflandırma
niyet (intent) bazlıdır, uydurma hacim rakamı içermez.

**A grubu — Ana kategori (yüksek hacim, yüksek rekabet, mutlaka başlıkta/kısa açıklamada)**

| Kelime | Niyet | Nerede geçmeli |
|---|---|---|
| akaryakıt fiyatları | Kategori | Başlık + kısa açıklama + uzun açıklama ilk paragraf |
| yakıt fiyatları | Kategori | Kısa açıklama + uzun açıklama |
| benzin fiyatları | Kategori | Uzun açıklama (2×) |
| motorin fiyatları | Kategori | Uzun açıklama (2×) |
| mazot fiyatı | Kategori (halk dili) | Uzun açıklama (1×) |
| lpg fiyatları | Kategori | Uzun açıklama (1×) |

**B grubu — Uzun kuyruk (düşük rekabet, yüksek dönüşüm — asıl kazanç burada)**

| Kelime | Niyet |
|---|---|
| en ucuz benzin nerede | Karar anı |
| yakınımdaki akaryakıt istasyonu | Konum |
| en yakın benzinlik | Konum |
| akaryakıt zam takibi / zam var mı | Haber |
| istasyon fiyat karşılaştırma | Karşılaştırma |
| yakıt maliyeti hesaplama | Hesap |
| depo doldurma maliyeti | Hesap |
| il il akaryakıt fiyatları | Liste |
| bugün benzin ne kadar | Güncel |

**C grubu — Marka kelimeleri (organik trafiğin sessiz kaynağı)**

Shell, Opet, Petrol Ofisi, BP, TotalEnergies, Türkiye Petrolleri (TP), Aytemiz.

> ⚠️ **Kural:** Marka adları **yalnızca uzun açıklama içinde, "desteklenen markalar"
> bağlamında ve düz metin olarak** geçmelidir. Başlıkta veya kısa açıklamada başka bir
> markanın adını kullanmak Play'in fikri mülkiyet politikası kapsamında şikâyet ve
> kaldırma riski doğurur. Ekran görüntülerinde marka logosu kullanılmaz.

### 5.2 Başlık (≤30 karakter)

| Öneri | Karakter | Değerlendirme |
|---|---|---|
| **`Fullet: Akaryakıt Fiyatları`** | 27 | ✅ **Önerilen.** Marka + en yüksek hacimli kategori kelimesi |
| `Fullet - Yakıt Fiyat Haritası` | 29 | Alternatif; "harita" farkı öne çıkarır |
| `Fullet: Benzin Motorin Fiyat` | 28 | İki kategori kelimesi; marka geri planda kalır |

**Karar:** `Fullet: Akaryakıt Fiyatları` ile başla. 60. günde Store Listing
Experiment ile 2. seçeneği test et.

### 5.3 Kısa açıklama (≤80 karakter)

| Öneri | Karakter |
|---|---|
| **`En ucuz değil, en mantıklı istasyon. Güncel akaryakıt fiyatları haritada.`** | 73 ✅ |
| `Yakınındaki akaryakıt fiyatları. Aracına göre en kârlı istasyonu bul.` | 69 |
| `6.000+ istasyon, güncel fiyat. Aracına göre gerçek maliyeti hesaplar.` | 69 |

**Karar:** Birinci seçenek. Hem farkı hem kategoriyi 73 karakterde veriyor.
Kısa açıklama, Play'de indeksleme ağırlığı en yüksek ikinci alandır — burada
"akaryakıt fiyatları" ifadesinin tam geçmesi kritiktir.

### 5.4 Uzun açıklama (≤4000 karakter)

Yazıya hazır tam metin **[Ek A](#ek-a--google-play-uzun-açıklama-metni)**'dadır.
Yapısal kurallar:

- **İlk 3 satır kritik:** Kullanıcı "devamını oku"ya basmadan bunu görür.
  Değer teklifi + en yüksek hacimli 2 kelime buraya sığmalı.
- Anahtar kelime yoğunluğu **%2-3'ü geçmemeli** (spam algısı hem kullanıcıda hem
  algoritmada zarar verir). Kelime doldurma yapılmaz.
- Emoji **başlık ayracı olarak** kullanılır (taranabilirlik ↑), cümle içinde değil.
- Sonda "Nasıl çalışıyor?" bölümü → güven inşası + uzun kuyruk kelime hasadı.
- Sonda "Desteklenen markalar" satırı → C grubu kelimeler için tek meşru yer.

### 5.5 Görsel varlıklar

Elde hazır: `play_store_assets/marketing/` altında 6 ekran görüntüsü ve feature
graphic; `play_store_assets/screenshots/` altında telefon + tablet setleri.

**Ekran görüntüsü sıralaması (dönüşümü belirleyen asıl faktör — ilk 3'ü kullanıcı
kaydırmadan görür):**

| # | Görsel | Üst başlık metni (caption) | Amaç |
|---|---|---|---|
| 1 | `05_akilli_mod.png` | **"En ucuz değil, EN MANTIKLI"** <br><sub>Aracının tüketimini ve yolu da hesaplar</sub> | Farkı ilk saniyede söyle |
| 2 | `02_fiyat_harita.png` | **"Yakınındaki tüm fiyatlar, tek haritada"** <br><sub>6.000+ istasyon · 7 marka</sub> | Kategori beklentisini karşıla |
| 3 | `04_depo_hesabi.png` | **"Bu depo sana kaça patlar?"** <br><sub>Tank + tüketim + yol maliyeti</sub> | Somut fayda |
| 4 | `03_istasyon_detay.png` | **"Fiyatın kaynağı yazıyor"** <br><sub>Doğrulayamadığımızı göstermiyoruz</sub> | Güven |
| 5 | `01_harita_genel.png` | **"Marka ve yakıt tipine göre filtrele"** | Yetenek genişliği |
| 6 | `06_gece_modu.png` | **"Gece sürüşünde göz yormaz"** | Kalite algısı |

> **Caption kuralı:** Metin görselin **üst %25'inde**, en az 60 px yüksekliğinde,
> yüksek kontrastlı olmalıdır. Play'de görseller küçük thumbnail olarak görülür;
> ekran görüntüsünün kendisi okunmaz, **caption okunur.**

**Feature graphic (1024×500):** `feature_graphic_1024x500_new.png` mevcut. Üzerinde
tek cümle olmalı: *"En ucuz değil, en mantıklı istasyon."* Feature graphic'te üç
satırlık metin okunmaz.

**Tanıtım videosu (30 sn, YouTube):** Sıfır bütçeyle ekran kaydından üretilebilir.
Play listesinde video varlığı dönüşümü belirgin artırır. Kurgu: *(0-3 sn)* zam haberi
ekranı → *(3-10 sn)* Fullet açılır, harita fiyatları gösterir → *(10-20 sn)* garaj
ekranı, araç seçimi, akıllı skorun değişmesi → *(20-27 sn)* yol tarifi → *(27-30 sn)*
logo + "En ucuz değil, en mantıklı." W4'te üretilir.

### 5.6 Yorum ve puan stratejisi

Play sıralamasında puan ve yorum hacmi, anahtar kelime kadar belirleyicidir.

| Aksiyon | Nasıl | Ne zaman |
|---|---|---|
| **Uygulama içi puan istemi** | Google Play In-App Review API — *doğru anda*: kullanıcı 3. kez yol tarifi aldıktan sonra veya akıllı skor kartını 5. kez gördükten sonra. Asla açılışta değil. | Bir sonraki sürümde (ürün ekibine talep) |
| **Her yoruma yanıt** | 24 saat içinde, kişisel, savunmacı olmayan dille. Olumsuz yorumlarda önce sorunu kabul et, sonra ne yaptığımızı söyle. | W1'den itibaren sürekli |
| **Yorum kampanyası** | Topluluk gruplarında "kullandıysan bir yorum bırak" çağrısı — **puan belirtmeden, karşılık vaat etmeden.** | W3, W7, W11 |
| **Negatif yorum → ürün girdisi** | Tekrarlayan şikâyetler aylık olarak listelenir ve ürün önceliğine dönüşür | Aylık |

> ⛔ **Kesin yasak:** Ödül karşılığı yorum, sahte hesapla yorum, "5 yıldız verirsen…"
> ifadesi. Play politikası ihlalidir ve uygulamanın kaldırılmasıyla sonuçlanabilir.
> Sıfır bütçeyle kurulan bir markanın kaybedecek en pahalı şeyi güvenilirliğidir.

### 5.7 A/B test planı (Play Console → Store Listing Experiments)

| Test | Ne zaman | Varyant A | Varyant B | Karar metriği |
|---|---|---|---|---|
| T1 · Kısa açıklama | W5 | "En ucuz değil, en mantıklı…" | "Yakınındaki akaryakıt fiyatları…" | Store listing conversion rate |
| T2 · İlk ekran görüntüsü | W8 | Akıllı mod | Harita + fiyatlar | Conversion rate |
| T3 · İkon | W11 | Mevcut | Yüksek kontrastlı varyant | Conversion + CTR |
| T4 · Başlık | W13 | `Fullet: Akaryakıt Fiyatları` | `Fullet - Yakıt Fiyat Haritası` | Conversion + arama görünürlüğü |

**Test disiplini:** Aynı anda tek değişken. Minimum 7 gün veya istatistiksel anlamlılık.
Trafik düşükse test süresi uzatılır — erken karar, yanlış karardır.

---

## 6. SOSYAL MEDYA VE VİRAL KANALLAR

### 6.1 Stratejinin kalbi: "Zam saatini sahiplen"

Fullet'in botları fiyatı **günde 4 kez** (06:20 / 12:20 / 18:20 / 00:20) topluyor ve
değişimi `fiyat_gecmisi` olarak kaydediyor. Türkiye'de akaryakıt zamları geleneksel
olarak **gece yarısı** yürürlüğe girer ve zam söylentisi akşam saatlerinde sosyal
medyada patlar. Bu, sıfır bütçeli bir markanın bulabileceği en değerli şeydir:
**tekrar eden, öngörülebilir, yüksek arama hacimli bir gündem ve o gündemde
kimsede olmayan veri.**

**Mekanizma:**

```
Zam/indirim tespiti (bot verisi)
        ↓
15 dakika içinde görsel kart üretimi (şablon hazır)
        ↓
X (öncelik) → Instagram Story/Reels → TikTok
        ↓
"Depon boşsa bu gece doldur" + uygulama linki
        ↓
Aramada "zam var mı" trafiği + kurulum
```

**Kritik disiplin:** Zam bilgisi **doğrulanmadan paylaşılmaz.** Yanlış zam duyurusu
yapan hesap, iki hafta içinde güvenilirliğini kaybeder. Elimizde teyit mekanizması
(marka kaynaklı veri) olması bizim tek avantajımızdır — onu harcamayız.

### 6.2 Kanal stratejisi

| Kanal | Rol | Format | Frekans | Öncelik |
|---|---|---|---|---|
| **X (Twitter)** | **Otorite ve haber kanalı.** Zam gündemi burada dönüyor; alıntılanma ve gazetecilere ulaşma buradan olur | Fiyat kartı görseli + kısa metin, thread'ler, alıntı yanıtları | Günde 1-3, zam günlerinde 5-8 | ★★★ |
| **Instagram Reels** | **Kitle kanalı.** P2 segmenti burada | 15-30 sn dikey video, ekran kaydı + altyazı | Haftada 3 | ★★★ |
| **TikTok** | **Viral kanal.** En yüksek organik erişim potansiyeli, en düşük takipçi bağımlılığı | 15-25 sn, hızlı kurgu, trend ses | Haftada 3-4 | ★★★ |
| **YouTube Shorts** | Reels/TikTok içeriğinin yeniden kullanımı; arama uzun ömürlü | Aynı dikey videolar | Haftada 3 (repost) | ★★ |
| **Instagram Feed/Story** | Topluluk ve destek | Fiyat kartları, anket, soru-cevap | Günlük story, haftada 2 feed | ★★ |

> **Üretim kuralı:** Tek bir dikey video çekilir, **4 kanala birden** yüklenir
> (TikTok → Reels → Shorts → Story). Sıfır bütçeli ekip için içerik başına maliyeti
> dörde bölen tek yöntem budur. TikTok filigranı olan video Reels'te erişim cezası
> alır — **her zaman filigransız orijinal dosya** kullanılır.

### 6.3 İçerik pilarları

| # | Pilar | Ağırlık | Amaç | Örnek |
|---|---|---|---|---|
| **1** | **Zam/İndirim Haberi** | %35 | Erişim + otorite | "🔴 Bu gece 00:00'dan itibaren motorine 1,42 TL zam. 60 litrelik depoda 85 TL fark." |
| **2** | **Veri/İçgörü** | %25 | Alıntılanma, basın | "İstanbul'da aynı marka, iki ilçe: litrede 0,90 TL fark. İşte harita." |
| **3** | **Eğitim/Mit yıkma** | %20 | Fark anlatımı | "3 km öteye gidip ucuz benzin almak kâr mı? Hesabı yapalım." |
| **4** | **Ürün gösterimi** | %15 | Dönüşüm | "Garajına aracını ekleyince harita nasıl değişiyor?" |
| **5** | **Topluluk/Şeffaflık** | %5 | Güven | "Fiyatı nasıl topluyoruz? Botlarımızı anlatıyoruz." |

### 6.4 İlk 20 içerik fikri (üretim sırası)

**Zam/İndirim (Pilar 1)**
1. "Zam geldi" kartı şablonu — her zam gecesi tekrarlanan sabit format
2. "Bu zam senin depona kaç TL?" — 40/50/60/80 litre için tablo
3. "Zam öncesi son 6 saat" geri sayım story serisi
4. İndirim haberi — zam kadar paylaşılır, daha az rekabet var

**Veri/İçgörü (Pilar 2)**
5. "Türkiye'nin en pahalı ve en ucuz 5 ili" — aylık seri
6. "Aynı şehirde iki uçtaki istasyon arasında ne kadar fark var?"
7. "Son 30 günde benzin/motorin nasıl hareket etti" — grafik
8. "Hafta içi mi hafta sonu mu daha pahalı?" — veri sorusu
9. "İl bazlı ilan fiyatı ne demek?" — kimsenin bilmediği ama herkesin etkilendiği konu

**Eğitim/Mit yıkma (Pilar 3)**
10. **"3 km uzaktaki ucuz benzin tuzağı"** — *amiral gemisi içerik, en yüksek viral potansiyel*
11. "Depoyu full doldurmak mı, yarım mı? Ağırlık gerçekten yakıyor mu?"
12. "Klima yakıtı ne kadar artırır?" — mevsimsel
13. "Yakıt lambası yandıktan sonra kaç km gidebilirsin?"
14. "LPG gerçekten ne kadar tasarruf ettiriyor?" — P4 segmenti

**Ürün (Pilar 4)**
15. "Garaj nedir, neden aracını eklemelisin?" — 20 sn ekran kaydı
16. "Sürüş modu: telefona bakmadan en yakın istasyon"
17. "Favori istasyonunu takip et"
18. "Fiyatın yanındaki ✓ işareti ne demek?"

**Topluluk (Pilar 5)**
19. "Fiyatı nasıl topluyoruz?" — botların günde 4 kez çalışması, şeffaflık
20. "Bilmediğimiz fiyatı neden göstermiyoruz?" — marka değeri içeriği

### 6.5 Viral tetikleyici formüller

| Formül | Şablon | Neden işler |
|---|---|---|
| **Somut TL** | "Bu zam 60 litrelik depoda **85 TL** demek." | Yüzde soyut, TL somut. Paylaşılan hep TL'dir. |
| **Karşıt sezgi** | "Ucuz benzine gitmek seni **zarara** sokabilir." | Beklenti kırılması = paylaşım |
| **Yerellik** | "Ankara'da bugün en ucuz motorin şurada." | Şehir etiketi = yerel gruplarda paylaşım |
| **Geri sayım** | "Zam'a 4 saat kaldı." | Aciliyet = kaydetme + paylaşma |
| **Kanıt** | Ekran kaydı, gerçek fiyat, gerçek istasyon | İddia değil kanıt = güven |

### 6.6 Haftalık yayın ritmi (sabit takvim)

| Gün | X | Reels/TikTok/Shorts | Story |
|---|---|---|---|
| Pazartesi | Haftalık fiyat özeti | — | Anket |
| Salı | Veri/içgörü kartı | **Video 1** (Pilar 3 veya 2) | Video tanıtımı |
| Çarşamba | Soru-cevap / alıntı yanıtı | — | Kullanıcı mesajı paylaşımı |
| Perşembe | İl karşılaştırma kartı | **Video 2** (Pilar 4) | — |
| Cuma | Hafta sonu yol tavsiyesi | — | Anket sonucu |
| Cumartesi | — | **Video 3** (Pilar 3) | — |
| Pazar | Haftaya bakış | — | — |
| **Her zam gecesi** | **Öncelikli, plan dışı, 15 dk içinde** | Ertesi gün özet video | Geri sayım |

---

## 7. TOPLULUK VE GERİLLA PAZARLAMA

### 7.1 Altın kural

> **Önce katkı, sonra bağlantı.**
> Hiçbir topluluğa ilk mesajında uygulama linkiyle girilmez. Her toplulukta önce
> **kimliğini açıkla** ("uygulamayı ben yaptım"), sonra **karşılıksız bir değer bırak**
> (o gruba özel fiyat verisi, cevap, analiz), sonra isteyen sorarsa link ver.
> Bu bir nezaket kuralı değil, **etkinlik kuralıdır**: gizlenen tanıtımcı banlanır,
> açık geliştirici desteklenir.

### 7.2 Kanal kanal giriş planı

#### A. Ekşi Sözlük

| | |
|---|---|
| **Neden** | Google'da yüksek sıralanır — bir entry yıllarca arama trafiği getirir. Türkiye'de "X uygulaması nasıl" aramasının cevabı burasıdır. |
| **Nasıl** | `fullet` başlığı açılmaz (reklam algısı + silinme). Bunun yerine **mevcut ilgili başlıklara** faydalı entry: `akaryakıt zammı`, `benzin fiyatları`, `en ucuz benzin`, `motorin fiyatı`. Entry gerçek bir bilgi içermeli; uygulama adı en fazla bir kez, cümle sonunda geçmeli. |
| **Risk** | Reklam algısı → entry silinir, yazar suspend olur. **Çoklu hesap kesinlikle kullanılmaz.** |
| **Ölçüm** | Play Console → Acquisition → yönlendiren web sitesi; `eksisozluk` referansı |
| **Frekans** | Ayda 2-3 entry, gündem varken |

#### B. Reddit (r/Turkey, r/otomobil, r/KGBTR, r/Turkish)

| | |
|---|---|
| **Neden** | Yüksek etkileşimli, teknoloji dostu, geliştirici hikâyesine sıcak bakan kitle |
| **Nasıl** | **"Kendim yaptım" (I made this) formatı en güçlüsüdür.** Başlık: *"Yakıt fiyatlarını karşılaştıran bir uygulama yaptım — ama sadece fiyatı değil, o istasyona gitme maliyetini de hesaplıyor"*. Gövde: neden yaptığın, nasıl çalıştığı (botlar, günde 4×), ne yapamadığı (dürüstlük!). Yorumların hepsine cevap ver. |
| **Risk** | Alt forumun self-promotion kuralı — **paylaşmadan önce mutlaka kural sayfası okunur**, gerekiyorsa modlara önce mesaj atılır |
| **Ölçüm** | Paylaşım günü kurulum sıçraması |
| **Frekans** | Alt forum başına **en fazla 3 ayda 1**. Aradaki sürede normal kullanıcı olarak katıl. |

#### C. Facebook grupları (P1 ve P3'ün ana yatağı)

| | |
|---|---|
| **Hedef gruplar** | Moto-kurye grupları (şehir bazlı), yemek/kargo kurye grupları, taksici/dolmuşçu grupları, nakliyeci/şoför grupları, LPG'li araç grupları, marka/model araç grupları |
| **Nasıl** | ① Gruba katıl, 1 hafta sadece oku ve yorum yap. ② Grubun işine yarayan bir gönderi paylaş (o şehrin bugünkü en ucuz 5 istasyonu — **link olmadan, düz görsel**). ③ İnsanlar "nereden baktın" diye sorar. ④ Yorumda uygulamayı söyle. ⑤ Yönetici izniyle sabit gönderi iste. |
| **Risk** | Link içeren gönderiler otomatik silinir/spam işaretlenir. **Önce görsel, sonra link.** |
| **Ölçüm** | Şehir bazlı kurulum artışı, grup gönderi etkileşimi |
| **Hedef** | 90 günde 25-40 aktif grupta tanınırlık |

#### D. WhatsApp / Telegram şoför ve kurye grupları

| | |
|---|---|
| **Neden** | **En yüksek dönüşümlü kanal.** Kapalı, güven yüksek, mesaj görülme oranı ~%100 |
| **Nasıl** | Doğrudan girilemez — gruplara ancak bir üye aracılığıyla girilir. Facebook gruplarında tanışılan kişilere "grubunuza faydalı olur mu?" diye sor. **Paylaşılabilir bir varlık** üret: her akşam 20:00'de o şehrin en ucuz 5 istasyonunun görseli — insanlar bunu kendileri gruplarına atar. |
| **Risk** | Spam algısı → engellenme. Asla toplu mesaj atılmaz. |
| **Ölçüm** | Görselin geri dönüşü (kaç gruptan bahsedildi), kurulum eğrisi |

#### E. Otomobil forumları (DonanımHaber, Technopat, marka forumları)

| | |
|---|---|
| **Neden** | Uzun ömürlü SEO değeri + teknik kitle + P4 (LPG) segmenti burada yoğun |
| **Nasıl** | "Geliştirici" olarak konu aç (çoğu forumun buna izin veren alt bölümü vardır). Konuyu **canlı tut**: her sürüm notunu buraya yaz, gelen isteklere cevap ver, yapılanları geri bildir. Forum kullanıcısı, isteği yapılan geliştirici için gönüllü elçi olur. |
| **Risk** | Ölü konu = itibar kaybı. Açtığın konuyu 90 gün boyunca besleyemeyeceksen açma. |
| **Ölçüm** | Konu görüntülenme, yönlendiren trafik |

#### F. Fiziksel gerilla (düşük maliyet, yüksek etki — P1'e özel)

| Taktik | Nasıl | Maliyet |
|---|---|---|
| **QR sticker** | Kurye bekleme noktaları, moto park alanları, esnaf panoları. Üzerinde tek cümle: *"Zam gecesini kaçırma. Yakınındaki en mantıklı istasyon."* + QR | ~200-400 TL / 200 adet (bütçe dışı sayılmaz, cepten karşılanabilir minimum) |
| **Kurye kurye tanıtım** | Bir yemek platformu bekleme alanında 1 saat: 20-30 kuryeye birebir göster. Doğrudan kurulum + geri bildirim + WhatsApp grubu erişimi | 0 TL, 1 saat |
| **Esnaf/oto sanayi** | Oto elektrikçi, LPG dönüşümcü, lastikçi — panoya QR kart | 0 TL |

> **Not:** Fiziksel taktikler ölçülemez sanılır ama ölçülebilir: **her fiziksel
> materyal için ayrı bir kısa link** (bit.ly/benzeri) kullanılır ve tıklama sayısı
> takip edilir.

#### G. Basın ve mikro-influencer (ücretsiz)

| | |
|---|---|
| **Hedef** | Otomotiv YouTube kanalları (10-100 bin abone), teknoloji haber siteleri (Webrazzi, ShiftDelete, Technopat, DonanımHaber haber tarafı), yerel haber siteleri |
| **Açı** | "Tek kişi tarafından geliştirilen, kendi veri botlarıyla çalışan yerli uygulama" hikâyesi + **veri içgörüsü** ("Türkiye'de aynı ilde iki istasyon arasında X TL fark var") |
| **Nasıl** | Kısa, kişisel e-posta (şablon: [Ek D](#ek-d--basın--mikro-influencer-e-posta-şablonu)). Hazır basın kiti: 6 ekran görüntüsü, feature graphic, 100 kelimelik açıklama, 30 sn video |
| **Frekans** | Haftada 5 hedefli e-posta. 20 e-postadan 1-2 dönüş normaldir. |

### 7.3 Topluluk çalışmasının etik sınırları

| ✅ Yap | ⛔ Yapma |
|---|---|
| Kim olduğunu açıkla | Sahte kullanıcı gibi davran |
| Gruba önce değer bırak | İlk mesajda link at |
| Eleştiriyi kabul et, düzelt | Savunmaya geç, sil, engelle |
| Grup kurallarını oku | Kural bilmeden paylaş |
| Tek hesapla, gerçek kimlikle | Çoklu hesap / sahte hesap |
| Rakibi hiç anma | Rakip hakkında olumsuz yorum yaz |

---

## 8. RETENTION VE ETKİLEŞİM

### 8.1 Retention neden edinmeden önemli

Yakıt alma döngüsü ortalama **5-7 gün**dür (kurye için 1-2 gün). Bu, uygulamanın
doğal kullanım aralığının **haftalık** olduğu anlamına gelir. Haftalık kullanımlı bir
uygulamada kullanıcı, üç hafta üst üste açmazsa uygulamayı unutur ve siler.

Sıfır bütçeli bir üründe **retention, edinmenin kendisidir**: elde tutulan her
kullanıcı, yeni kullanıcı satın almak için harcanmayan paradır ve tavsiye kaynağıdır.

### 8.2 Bildirim senaryo matrisi

Mevcut altyapı: `flutter_local_notifications` + `timezone` ile yerel zamanlı
bildirimler çalışıyor. Aşağıdaki senaryolar bu altyapı üzerine kurulur; sunucu
tarafı gerektirenler ayrıca işaretlenmiştir.

| # | Senaryo | Tetikleyici | Zamanlama | Örnek metin | Beklenen etki | Altyapı |
|---|---|---|---|---|---|---|
| **N1** | **Zam öncesi uyarı** | Zam tespiti | Yürürlükten **6 saat önce** (≈18:00) | "⛽ Bu gece motorine zam geliyor. Depon boşsa bugün doldur — 60 litrede ~85 TL fark." | **En yüksek etkili bildirim.** Açılma oranı diğerlerinin 3-5 katı | Sunucu (gelecek sürüm) |
| **N2** | Depo döngüsü hatırlatması | Son açılıştan 5 gün | 09:30 | "Yakıt zamanı mı? Yakınındaki güncel fiyatlar hazır." | D7 retention | ✅ Mevcut |
| **N3** | Garaj boş hatırlatması | Kurulumdan 24 saat, garaj boşsa | 19:00 | "Aracını ekle, hesabı sana göre yapalım. 30 saniye sürer." | Garaj doluluk ↑ → kişiselleşme ↑ | ✅ Mevcut |
| **N4** | Favori istasyonda fiyat düştü | Favori + fiyat düşüşü | Anında (09:00-21:00 arası) | "Takip ettiğin [istasyon]'da motorin 0,60 TL düştü." | Favori kullanımı ↑, geri dönüş ↑ | Sunucu (gelecek) |
| **N5** | **Haftalık tasarruf karnesi** | Haftalık | Pazar 11:00 | "Bu hafta Fullet ile ~140 TL fark ettin. Detayları gör →" | **Alışkanlık döngüsünün kilit taşı** | Yerel hesaplama mümkün |
| **N6** | İl bazlı indirim | İndirim tespiti | Anında | "İyi haber: [il]'de benzin 0,45 TL ucuzladı." | Olumlu marka çağrışımı | Sunucu (gelecek) |
| **N7** | Uzun yol öncesi | 7 gündür açılmadı + hafta sonu | Cuma 17:00 | "Hafta sonu yola mı çıkıyorsun? Rota üstündeki fiyatlara bak." | Uyuyan kullanıcı geri kazanımı | ✅ Mevcut |

### 8.3 Bildirim yorgunluğu sınırları (pazarlık edilemez)

| Kural | Değer |
|---|---|
| Haftada maksimum bildirim | **3** |
| Sessiz saatler | 22:00 – 08:00 (zam uyarısı dahil, istisnasız) |
| Arka arkaya açılmayan bildirim sonrası | 3 kez açılmadıysa frekansı yarıya düşür |
| Kullanıcı kontrolü | Ayarlarda kategori bazlı açma/kapama (zam / hatırlatma / favori / haftalık) |
| Metin kuralı | Her bildirimde **somut TL** olsun; "haberler var" tipi boş bildirim yok |

> **İlke:** Bir bildirim, kullanıcının uygulamayı silmesine sebep olabiliyorsa
> gönderilmez. Bildirim bütçesi kullanıcının sabrıdır ve yenilenemez.

### 8.4 Etkileşim döngüleri

**Döngü 1 — Haftalık tasarruf karnesi (birincil alışkanlık döngüsü)**

```
Kullanıcı istasyon seçer → yol tarifi alır
        ↓
Uygulama "bu seçimde ne kadar fark ettiğini" biriktirir
        ↓
Pazar 11:00 → "Bu hafta ~140 TL fark ettin"
        ↓
Uygulama açılır → karne ekranı → paylaşılabilir görsel
        ↓
Kullanıcı paylaşır (viral kanal) → yeni kullanıcı
```
Bu döngü hem retention hem edinme üretir. **Ürün önceliği listesinde bir numaradır.**

**Döngü 2 — Zam gündemi döngüsü (haftalık dış tetikleyici)**

```
Zam söylentisi (sosyal medya) → Fullet içeriği (X/Reels) → uygulama açılır
        → depo doldurulur → "iyi ki bildirdiler" → sadakat
```

**Döngü 3 — Garaj kişiselleştirme döngüsü**

```
Araç eklenir → akıllı skor anlamlı hale gelir → öneri isabetli olur
        → kullanıcı güvenir → tekrar açar → geçiş maliyeti artar
```
Bu yüzden **garaj doluluk oranı, D7 retention'ın en güçlü öncü göstergesidir.**
Haftalık takip edilmelidir (`garage_vehicle_set` event'i).

### 8.5 Retention hedef bantları

| Metrik | Kategori tipik | Fullet hedefi (90 gün) | Öncü gösterge |
|---|---|---|---|
| D1 | %20-25 | **%35** | Onboarding tamamlama oranı |
| D7 | %8-12 | **%15** | Garaj doluluk oranı |
| D30 | %3-6 | **%8** | Bildirim izni oranı + favori kullanımı |
| Ay içi oturum/kullanıcı | 3-4 | **6** | Zam bildirimi açılma oranı |

---

## 9. MONETİZASYON YOL HARİTASI

### 9.1 Temel karar: Şimdi para kazanmıyoruz

**Öneri: İlk 6 ay hiçbir gelir modeli devreye alınmaz.**

Gerekçe:
1. **Reklamın matematiği bu ölçekte çalışmaz.** Türkiye'de bir uygulamanın binlik
   gösterim geliri (eCPM) düşüktür. Anlamlı bir gelir için aylık yüz binlerce
   gösterim gerekir; bu da on binlerce aktif kullanıcı demektir. **Aktif kullanıcı
   sayısı buraya gelmeden reklam koymak, gelir getirmez ama retention'ı düşürür.**
2. **Reklamsızlık şu anda bir pazarlama silahıdır.** Kategorinin en yaygın şikâyeti
   reklam yoğunluğudur. "Reklamsız" ifadesi bugün bizim ASO ve topluluk
   anlatımızın parçasıdır; bunu erken harcamak stratejik hatadır.
3. **Vergi/muhasebe yükü şu an gereksizdir.** Aylık birkaç yüz lira için idari yük
   almanın anlamı yoktur.

**Gelir açma eşiği:** **Aylık 30.000+ aktif kullanıcı (MAU) ve D7 ≥ %12.**
Bu eşiğin altında hiçbir gelir modeli açılmaz. Eşik geldiğinde aşağıdaki faz sırası
uygulanır.

### 9.2 Faz sırası

| Faz | Ne zaman | Model | Beklenen katkı | UX riski |
|---|---|---|---|---|
| **Faz 0** | Şimdi – ~6 ay | **Gelir yok.** Tek hedef kullanıcı ve veri birikimi | 0 | — |
| **Faz 1** | MAU ≥ 30K | **AdMob — kontrollü ve sınırlı** | Düşük–orta | Orta (kurallarla yönetilir) |
| **Faz 2** | MAU ≥ 50K, 6+ ay veri geçmişi | **B2B veri ve API** | **En yüksek marj** | **Sıfır** |
| **Faz 3** | MAU ≥ 100K | **Fullet Pro (abonelik)** | Orta–yüksek, tekrarlayan | Düşük |
| **Faz 4** | MAU ≥ 150K | **İstasyon/marka iş ortaklığı** | Yüksek | Orta (şeffaflıkla yönetilir) |

### 9.3 Faz 1 — AdMob: kesin UX kuralları

Reklam açıldığında aşağıdaki kurallar **pazarlık konusu değildir**. Bir uygulamayı
reklam öldürmez; *kötü yerleştirilmiş reklam* öldürür.

| ✅ İzinli | ⛔ Yasak |
|---|---|
| Haberler listesinde native reklam (içerik akışının parçası) | **Harita ekranında hiçbir reklam** — ürünün kalbi burasıdır |
| Ayarlar / hakkında ekranında banner | İstasyon detay panelinde (karar anı) reklam |
| **Ödüllü reklam**: kullanıcı isterse izler, karşılığında bir premium özellik açılır | Açılışta veya harita yüklenirken interstitial |
| Oturumda en fazla 1 tam ekran reklam, o da **çıkış niyeti** anında | Yol tarifi akışını kesen reklam |
| — | Otomatik oynayan sesli video reklam |

**Ödüllü reklam modeli (önerilen ilk adım):** Kullanıcı 30 saniyelik bir reklam
izleyerek "1 haftalık fiyat alarmı" açar. Bu model reklamı **kullanıcının seçtiği bir
takasa** dönüştürür; zorlama içermez, eCPM'i banner'ın kat kat üstündedir ve
retention'a zarar vermez.

### 9.4 Faz 2 — B2B veri ve API (**stratejik olarak en değerli hat**)

Fullet, farkında olunmadan **Türkiye'nin en ayrıntılı bağımsız akaryakıt fiyat
zaman serisi veri tabanlarından birini** üretiyor: 7 marka, 6.000+ istasyon, günde
4 ölçüm, il ve istasyon kırılımında geçmiş.

Bu verinin alıcıları:

| Alıcı | İhtiyaç | Ürün |
|---|---|---|
| Filo yönetim şirketleri | Rota üzeri yakıt maliyeti optimizasyonu | API aboneliği |
| Lojistik/nakliye firmaları | Maliyet planlama, bütçeleme | Aylık rapor + API |
| Medya / haber siteleri | Zam haberi için doğrulanmış veri, grafik | Aylık veri lisansı, atıf zorunlu |
| Akademi / araştırma | Fiyat davranışı çalışmaları | İndirimli/ücretsiz (itibar yatırımı) |
| Finans / analiz | Enflasyon ve emtia göstergesi | Premium veri |

**Neden UX riski sıfır:** Kullanıcı bundan hiç etkilenmez. Satılan şey **anonim
ve toplu (aggregate) fiyat verisidir** — kişisel veri, konum verisi, kullanıcı
davranışı **asla satılmaz, paylaşılmaz.** Bu ilke KVKK uyumu ve Play Data Safety
beyanı açısından da zorunludur ve pazarlamada bir güven mesajı olarak kullanılır.

**İlk adım (bugün yapılabilir, bedava):** Aylık bir **"Türkiye Akaryakıt Fiyat
Raporu"** yayımla — halka açık, ücretsiz, atıf isteyen. Bu rapor hem içerik pazarlaması
(§6 Pilar 2), hem basın kancası, hem de B2B tarafına giden kapıdır. Gazeteciler bu
raporu kullanmaya başladığında Fullet, "bir uygulama" olmaktan çıkıp **referans
kaynağı** olur.

### 9.5 Faz 3 — Fullet Pro (abonelik)

| Ücretsiz (her zaman) | Pro |
|---|---|
| Harita, tüm fiyatlar, akıllı skor | + Sınırsız fiyat alarmı (eşik fiyat) |
| 1 araç (garaj) | + Sınırsız araç / filo profili |
| Favoriler, sürüş modu | + Rota üzeri optimizasyon (A→B arası en kârlı istasyon) |
| Fiyat trendi (son değişimler) | + Uzun dönem fiyat geçmişi ve grafik |
| — | + Reklamsız (Faz 1 açıldıysa) |
| — | + Haftalık/aylık gider raporu (dışa aktarma) |

**Fiyatlama ilkesi:** Aylık bedel, kullanıcının bir depoda ettiği ortalama farkın
**altında** olmalıdır. Ürün kendi bedelini ilk depoda ödemiyorsa satılmaz.
Yıllık abonelikte en az %35 indirim.

**Kritik kural:** **Bugün ücretsiz olan hiçbir özellik Pro'ya taşınmaz.** Pro,
yalnızca *yeni* değerden oluşur. Mevcut özelliği paralı yapmak, kullanıcı tabanını
ve yorum ortalamasını yok eder.

### 9.6 Vergi ve yasal çerçeve — bilinmesi gerekenler

> ⚠️ **Bu bölüm bilgilendirme amaçlıdır, mali veya hukuki danışmanlık değildir.
> Gelir elde etmeye başlamadan önce mutlaka bir mali müşavire danışılmalıdır.**

Endişen yerinde ve önemli: gelir elde etmek bir vergi yükümlülüğü doğurur. Ancak
Türkiye'de **tam olarak senin durumundaki geliştiriciler için tasarlanmış özel bir
istisna** vardır ve bu, işi düşündüğünden çok daha basit hale getirir.

**Gelir Vergisi Kanunu Mükerrer Madde 20/B — Sosyal içerik üreticiliği ve mobil
uygulama geliştiriciliği kazanç istisnası:**

| Konu | Bilinen çerçeve |
|---|---|
| **Kimi kapsar** | Akıllı telefon/tablet uygulamaları geliştirip **elektronik uygulama paylaşım ve satış platformları** (Google Play, App Store) üzerinden gelir elde eden **gerçek kişiler** |
| **Hangi gelir türleri** | Uygulama satışı, uygulama içi satış, **reklam gelirleri**, sponsorluk ve ücretlendirme gelirleri (Genel Tebliğ'de açıkça sayılmıştır) |
| **Nasıl işler** | Türkiye'deki bir bankada **bu gelire özel bir hesap** açılır; **tüm** platform geliri bu hesaba yatar. Banka, yatan tutar üzerinden **%15 gelir vergisi stopajı** yapar ve devlete öder. |
| **Sonuç** | Yıllık gelir, kanunda belirtilen üst sınırın altındaysa: **beyanname verilmez, defter tutulmaz, KDV mükellefiyeti doğmaz.** Banka kesintisi nihai vergidir. |
| **Üst sınır** | GVK 103. maddedeki tarifenin 4. gelir dilimindeki tutar (her yıl yeniden değerlemeyle artar — **2026 rakamını mali müşavirden teyit et**). Uygulamada bu sınır milyonlarca lira mertebesindedir; başlangıç seviyesindeki bir gelir bunun çok altında kalır. |
| **Gerekli işlem** | Vergi dairesinden **istisna belgesi** alınır ve bankaya ibraz edilir. |

**Pratikte ne demek:** AdMob'dan gelen paranın Türkiye'deki belirlenmiş banka hesabına
gelmesini sağlarsan, bankanın kestiği %15 dışında ek bir vergi yükümlülüğün, defter
tutma zorunluluğun veya şirket kurma ihtiyacın **büyük olasılıkla doğmaz.**

**İlave not — Genç Girişimci İstisnası:** 29 yaş altındaysan ve ileride şahıs şirketi
kurma yoluna gidersen, ayrıca üç yıl süreyle geçerli bir kazanç istisnası ve BAĞ-KUR
prim teşviki mevcuttur. İki istisna aynı anda kullanılamaz; hangisinin avantajlı
olduğu gelir düzeyine göre değişir.

**Aksiyon sırası (gelir açmadan önce):**
1. Mali müşavir görüşmesi (1 saat, birkaç yüz TL) — Mük. 20/B kapsamı ve 2026 sınırı
   teyit edilir
2. Vergi dairesinden istisna belgesi
3. Belirlenmiş banka hesabı açılışı
4. AdMob / Play ödeme profilinin bu hesaba bağlanması
5. **Sonra** reklam açılır

> **Özet tavsiye:** Vergi endişesi, gelir modelini ertelemek için geçerli bir sebep
> değil — çünkü çözümü hazır ve basit. Ama **kullanıcı sayısı yetersizken reklam
> açmamak** için geçerli bir sebep vardır: matematiği tutmaz ve ürüne zarar verir.
> Bu yüzden Faz 0'da kal, MAU 30K eşiğini bekle.

---

## 10. 30-60-90 GÜNLÜK EYLEM PLANI

**Başlangıç:** 10 Ağustos 2026 (Pazartesi) · **Bitiş:** 8 Kasım 2026
**Varsayılan kapasite:** Haftada 8-10 saat, tek kişi. **Bütçe: 0 TL.**

### AY 1 (W1-W4) — TEMEL: Ölç, düzelt, ilk kanalı aç

**Ayın amacı:** Kör uçuşu bitirmek ve mağaza sayfasını dönüşen bir varlığa çevirmek.
Ay sonunda bir kanalda (X) düzenli yayın yapan bir hesap ve optimize edilmiş bir
Play sayfası olmalı.

| Hafta | İş | Kanal | Çıktı | Metrik | Süre |
|---|---|---|---|---|---|
| **W1** ✅ | **Taban ölçüm raporu**: Play Console (kurulum, dönüşüm, arama terimleri, ülke/cihaz kırılımı) + Firebase (D1/D7, huni, garaj doluluk) mevcut değerleri tek sayfaya yazılır | — | `baseline.md` — **tamamlandı (7 Ağustos 2026)** | Tüm metriklerin bugünkü değeri | 3 sa |
| W1 ✅ | Sosyal hesapların açılması: X, Instagram, TikTok — aynı kullanıcı adı, aynı bio, aynı görsel kimlik. **YouTube kapsam dışı bırakıldı** (bkz. not) | Sosyal | 3 hesap canlı (`fullet_tr`) — **tamamlandı** | — | 2 sa |
| W1 ✅ | Fiyat kartı görsel şablonu: zam kartı, il karşılaştırma kartı, "en ucuz 5" kartı | Üretim | 3 şablon, `play_store_assets/marketing/fiyat_kartlari/` — **tamamlandı** | — | 3 sa |
| **W2** | **ASO güncellemesi**: yeni başlık, kısa açıklama, uzun açıklama ([Ek A](#ek-a--google-play-uzun-açıklama-metni)) yayına alınır | Play | Yeni store listing | Store conversion rate (7 gün sonra) | 2 sa |
| W2 | Ekran görüntüsü caption'ları eklenir, sıralama §5.5'e göre değiştirilir | Play | 6 yeni görsel | Conversion rate | 3 sa |
| W2 | X'te yayın başlar: günde 1 gönderi, ilk zam gecesi canlı yayın | X | 7+ gönderi | Erişim, takipçi | 3 sa |
| **W3** | **İlk viral deneme:** "3 km uzaktaki ucuz benzin tuzağı" videosu → TikTok + Reels + Shorts | Video | 1 video, 3 kanal | İzlenme, profil tıklaması, kurulum | 4 sa |
| W3 | 10 Facebook grubuna katılım (kurye + LPG + otomobil), 1 hafta sadece gözlem | Facebook | 10 grup üyeliği | — | 1 sa |
| W3 | Mevcut tüm Play yorumlarına yanıt | Play | %100 yanıt | Puan ortalaması | 1 sa |
| **W4** | **Reddit "kendim yaptım" gönderisi** (r/Turkey veya r/otomobil — kural okunarak) | Reddit | 1 gönderi + tüm yorumlara yanıt | Gönderi günü kurulum sıçraması | 3 sa |
| W4 | 30 sn tanıtım videosu → Play listesine eklenir | Play | Video canlı | Conversion rate | 3 sa |
| W4 | **Ay 1 değerlendirmesi**: taban ile karşılaştırma, ne işe yaradı | — | 1 sayfa rapor | Tüm KPI'lar | 1 sa |

**Ay 1 çıkış kriterleri:** ☑ Taban metrikler yazılı ☐ ASO güncellendi ☑ 3 sosyal
hesap düzenli yayında *(YouTube kalıcı olarak kapsam dışı — bkz. not)* ☐ İlk video
yayınlandı ☑ Play puanı ≥ 4,3 *(bugün: 5,0 — küçük örneklem, izlemeye devam)*

> **W1 kapanış notu (7 Ağustos 2026):** W1'in üç görevi de tamamlandı. YouTube,
> kullanıcının solo kapasite kararıyla **kalıcı olarak** plan dışı bırakıldı — bu,
> planın kendi kanal önceliğiyle çelişmiyor çünkü YouTube zaten §6.2'de en düşük
> öncelikli (★★) kanaldı; "Altın Üçlü" X/Instagram/TikTok'a odaklanma çıkış
> kriterini karşılar. Baseline analizi ayrıca kritik bir aktivasyon bulgusu ortaya
> çıkardı (onboarding "Atla" garaj adımını da atlıyor, `garage_vehicle_set` %18,3
> ile kırmızı alarmda) — bilinçli olarak bu hafta koda dokunulmadı, bulgu
> `URUN_TALEBI_ONBOARDING_GARAJ.md`'de backlog'a alındı. Detaylar: `baseline.md`.

---

### AY 2 (W5-W8) — İVME: Kanalları çoğalt, topluluğa gir

**Ayın amacı:** İçerik üretimini rutinleştirmek ve P1 (kurye) segmentine fiilen
girmek. Bu ay kurulum eğrisinde ilk gerçek sıçrama beklenir.

| Hafta | İş | Kanal | Çıktı | Metrik | Süre |
|---|---|---|---|---|---|
| **W5** | **§6.6 haftalık yayın takvimi tam uygulanır**: haftada 3 video + günlük X | Sosyal | 3 video, 7 gönderi | Erişim, takipçi artışı | 5 sa |
| W5 | **Facebook grup girişi başlar**: 5 grupta "şehrinin en ucuz 5 istasyonu" görseli (link yok) | Facebook | 5 gönderi | Yorum, "nereden baktın" sorusu sayısı | 2 sa |
| W5 | **A/B Test T1** başlatılır (kısa açıklama) | Play | Deney canlı | Conversion rate | 0,5 sa |
| W5 | LPG odaklı içerik (P4 segmenti) → LPG gruplarına | Facebook/Video | 1 video + 3 gönderi | Segment kurulumu | 2 sa |
| **W6** | **Fiziksel gerilla 1**: bir kurye bekleme noktasında 1 saat birebir tanıtım | Saha | 20-30 birebir gösterim | Kısa link tıklaması, kurulum | 2 sa |
| W6 | QR sticker tasarımı ve baskısı (minimum adet) | Saha | 200 sticker | Kısa link tıklaması | 2 sa |
| W6 | Otomobil forumlarında geliştirici konusu açılır (2 forum) | Forum | 2 konu | Görüntülenme, yönlendirme | 2 sa |
| **W7** | **İlk "Aylık Akaryakıt Fiyat Raporu" yayımlanır** (Eylül raporu) — blog/X thread + görsel | İçerik/Basın | 1 rapor | Paylaşım, alıntı, basın dönüşü | 5 sa |
| W7 | Basın/mikro-influencer erişimi: 20 hedefli e-posta ([Ek D](#ek-d--basın--mikro-influencer-e-posta-şablonu)) | Basın | 20 e-posta | Dönüş oranı, yayın sayısı | 3 sa |
| W7 | Yorum kampanyası (topluluk kanallarında) | Topluluk | — | Yorum sayısı, puan | 1 sa |
| **W8** | **A/B Test T2** (ilk ekran görüntüsü) | Play | Deney canlı | Conversion rate | 0,5 sa |
| W8 | Ekşi Sözlük: ilgili başlıklara 2-3 faydalı entry | Sözlük | 2-3 entry | Yönlendiren trafik | 1 sa |
| W8 | WhatsApp/Telegram grup erişimi: W5-W6'da tanışılan kişiler üzerinden | Kapalı grup | 3-5 grup | Kurulum sıçraması | 2 sa |
| W8 | **Ay 2 değerlendirmesi** + kanal verimlilik tablosu (hangi kanal kaç kurulum) | — | Rapor | Kanal başına kurulum | 1,5 sa |

**Ay 2 çıkış kriterleri:** ☐ Haftalık içerik ritmi 4 hafta kesintisiz ☐ 15+ grupta
tanınırlık ☐ İlk aylık rapor yayında ☐ En az 1 basın/influencer yayını ☐ D1 ≥ %30
☐ Kurulum: taban × 3

---

### AY 3 (W9-W13) — ÖLÇEKLE: İşe yarayanı ikiye katla, retention'ı kur

**Ayın amacı:** Ay 2'de en çok kurulum getiren **iki kanala** yoğunlaşmak, geri
kalanı bakım moduna almak; retention mekanizmalarını ürün tarafına sokmak.

| Hafta | İş | Kanal | Çıktı | Metrik | Süre |
|---|---|---|---|---|---|
| **W9** | **Kanal odaklanma kararı**: en verimli 2 kanala %70 emek, diğerleri bakım modu | — | Karar notu | Kanal başına kurulum maliyeti (saat) | 1 sa |
| W9 | Kazanan kanalda üretim iki katına çıkarılır | En verimli kanal | 2× içerik | Erişim, kurulum | 6 sa |
| W9 | **Ürün talebi #1 (retention):** uygulama içi puan istemi doğru anda | Ürün | Talep dokümanı | Yorum sayısı | 1 sa |
| **W10** | **Ürün talebi #2:** haftalık tasarruf karnesi + paylaşılabilir görsel (§8.4 Döngü 1) | Ürün | Talep dokümanı | D7, paylaşım sayısı | 2 sa |
| W10 | Bildirim senaryoları N2/N3/N7 metinleri optimize edilir | Ürün | Yeni metinler | Bildirim açılma oranı | 1 sa |
| W10 | Facebook grup sayısı 25-40'a çıkarılır | Facebook | +15 grup | Şehir bazlı kurulum | 3 sa |
| **W11** | **A/B Test T3** (ikon) | Play | Deney canlı | Conversion + CTR | 0,5 sa |
| W11 | Ekim ayı fiyat raporu | İçerik/Basın | 1 rapor | Alıntı, basın | 4 sa |
| W11 | İkinci Reddit gönderisi (farklı alt forum, farklı açı: veri hikâyesi) | Reddit | 1 gönderi | Kurulum sıçraması | 2 sa |
| W11 | Yorum kampanyası #2 | Topluluk | — | Yorum ≥ 100 | 1 sa |
| **W12** | **P3 segmenti açılışı**: şehirlerarası/ticari içerik serisi + nakliyeci grupları | Video/Facebook | 2 video, 5 grup | Motorin kullanıcı oranı | 4 sa |
| W12 | Basın erişimi ikinci dalga (20 e-posta, rapor verisiyle) | Basın | 20 e-posta | Yayın sayısı | 2 sa |
| **W13** | **A/B Test T4** (başlık) | Play | Deney canlı | Conversion | 0,5 sa |
| W13 | **90 gün kapanış raporu** + sonraki 90 günün planı | — | Rapor + plan | Tüm KPI'lar | 4 sa |
| W13 | Monetizasyon eşik kontrolü: MAU ≥ 30K mı? Evetse Faz 1 hazırlığı (mali müşavir görüşmesi) | İş | Karar | MAU | 2 sa |

**Ay 3 çıkış kriterleri:** ☐ İki ana kanalda istikrarlı büyüme ☐ D1 ≥ %35, D7 ≥ %15
☐ Play puanı ≥ 4,5, yorum ≥ 100 ☐ Kurulum: taban × 5-6 ☐ Marka araması ölçülebilir
☐ Sonraki 90 günün planı yazılı

---

### 10.1 Zam gecesi protokolü (plan dışı, her zam için geçerli)

Zam gecesi, ayın en değerli pazarlama fırsatıdır ve takvime yazılamaz — hazır olmak
gerekir.

| Saat | Aksiyon |
|---|---|
| **T-8 sa** | Söylenti tespiti (X gündemi, sektör kaynakları). **Doğrulanmadan paylaşılmaz.** |
| **T-6 sa** | Doğrulandıysa: X gönderisi + story geri sayımı + hazır kart görseli. "Depon boşsa bugün doldur — X litrede Y TL fark." |
| **T-3 sa** | Hatırlatma gönderisi + il bazlı fark tablosu |
| **T-0** | Zam yürürlükte: "Yeni fiyatlar haritada" + ekran görüntüsü |
| **T+8 sa** | Özet video (TikTok/Reels): "Dün gece ne oldu, kim ne kadar ödedi" |
| **T+24 sa** | Veri gönderisi: zammın il bazında yansıması |

**Hazırlık şartı:** Kart şablonu, metin taslakları ve görsel format **önceden hazır
olmalı**. Zam gecesinde tasarım yapılmaz; sadece rakam değiştirilip yayınlanır.
Hız, bu oyunda içeriğin kalitesinden daha değerlidir.

---

## 11. KPI PANOSU VE ÖLÇÜM MİMARİSİ

### 11.1 Kuzey yıldızı metrik

> **Haftalık yol tarifi alan benzersiz kullanıcı sayısı** (`directions_requested`
> event'i, haftalık benzersiz kullanıcı)

**Neden bu:** Kurulum sayısı yanıltıcıdır (kaldırılan kurulumlar dahildir), oturum
sayısı niyet göstermez. Yol tarifi almak, kullanıcının **gerçekten Fullet'in önerisine
göre davrandığı** andır. Ürünün değer üretip üretmediğini tek başına gösteren metrik
budur. Gelir modelinin (Faz 2/4) de temel para birimidir.

### 11.2 Mevcut event altyapısıyla ölçüm haritası

Firebase Analytics'te tanımlı event'ler doğrudan aşağıdaki soruların cevabıdır:

| Soru | Event | Nasıl okunur |
|---|---|---|
| Kaç kişi uygulamayı gerçekten kullandı? | `app_open` | DAU / MAU |
| Onboarding çalışıyor mu? | `onboarding_completed` ÷ `onboarding_skipped` | Tamamlama oranı hedefi ≥ %60 |
| **Kişiselleşme oluyor mu?** | `garage_vehicle_set` | **Garaj doluluk oranı — D7'nin en güçlü öncü göstergesi** |
| Kullanıcı istasyon inceliyor mu? | `station_tapped` | Oturum başına ortalama |
| **Değer üretiyor muyuz?** | `directions_requested` | **Kuzey yıldızı** |
| Hangi yakıt tipi baskın? | `fuel_type_changed` | Segment doğrulaması (motorin ↑ = P1/P3 geliyor) |
| Filtre kullanılıyor mu? | `brand_filter_changed` | Özellik benimseme |
| Akıllı mod görülüyor mu? | `smart_selection_seen` | Farkımız kullanıcıya ulaşıyor mu |
| Sadakat var mı? | `favorite_toggled` | Retention öncü göstergesi |
| Arama davranışı | `search_performed` | Eksik istasyon/marka tespiti |

### 11.3 Dönüşüm hunisi ve hedef bantları

```
Play sayfası görüntüleme
   │  ── Store conversion rate ── hedef ≥ %25
   ▼
Kurulum
   │  ── İlk açılış oranı ── hedef ≥ %85
   ▼
Onboarding tamamlama
   │  ── hedef ≥ %60
   ▼
Garaj doldurma (garage_vehicle_set)
   │  ── hedef ≥ %35   ★ en kritik eşik
   ▼
İstasyon inceleme (station_tapped)
   │  ── hedef ≥ %70
   ▼
Yol tarifi (directions_requested)   ★ KUZEY YILDIZI
   │  ── hedef ≥ %40
   ▼
7. gün geri dönüş (D7)  ── hedef ≥ %15
```

**Huni okuma kuralı:** Aylık olarak **en düşük dönüşümlü basamak** bulunur ve o ay
yalnızca o basamak üzerinde çalışılır. Aynı anda üç basamağı iyileştirmeye çalışmak,
hiçbirini iyileştirmemektir.

### 11.4 Haftalık pano (her Pazartesi 15 dakika)

| Metrik | Kaynak | Hedef yön |
|---|---|---|
| Yeni kurulum (7 gün) | Play Console | ↑ |
| Kaldırma oranı (uninstall) | Play Console | ↓ %30 altı |
| Store conversion rate | Play Console | ↑ |
| İlk 10 arama terimi | Play Console → Search terms | Marka araması payı ↑ |
| DAU / MAU (yapışkanlık) | Firebase | ↑ %20 üzeri |
| D1 / D7 | Firebase | ↑ |
| Kuzey yıldızı (haftalık `directions_requested` UU) | Firebase | ↑ |
| Garaj doluluk oranı | Firebase | ↑ |
| Play puanı ve yorum sayısı | Play Console | ↑ |
| Sosyal: erişim, takipçi, profil tıklaması | Platform panelleri | ↑ |
| Kanal başına kurulum tahmini | Play Console + kısa linkler | Odaklanma kararı için |

### 11.5 Aylık derinlemesine analiz (ayın ilk Pazartesi'si, 1 saat)

1. Kanal verimlilik tablosu: **kanal başına harcanan saat ÷ getirdiği kurulum**
2. Kohort retention: bu ayki kullanıcılar geçen aydan daha mı iyi tutunuyor
3. Huni: en zayıf basamak ve nedeni
4. Yorum analizi: tekrarlayan şikâyetler → ürün önceliği
5. Rakip hareketleri: store sayfası değişiklikleri, yeni özellikler
6. Karar: gelecek ay neyi bırakıyoruz, neyi ikiye katlıyoruz

### 11.6 Kırmızı bayraklar (görülürse plan durur, sebep aranır)

| Sinyal | Anlamı | İlk müdahale |
|---|---|---|
| Kaldırma oranı > %40 | Ürün beklentiyi karşılamıyor veya store sayfası yanlış vaat veriyor | Store vaatlerini ürünle karşılaştır; ilk oturum kaydını izle |
| D1 < %20 | Onboarding veya ilk deneyim kırık | Onboarding huni analizi, konum izni akışı |
| Play puanı < 4,0 | Kritik — organik keşfi öldürür | Tüm negatif yorumların kök neden analizi, acil düzeltme |
| Garaj doluluk < %20 | Farkımız kullanıcıya ulaşmıyor | Onboarding'de garaj vurgusu, N3 bildirimi |
| İçerik erişimi 3 hafta üst üste düşüyor | Format yorulmuş | Pilar dağılımını değiştir, yeni format dene |
| Bir grupta/forumda olumsuz tepki | Spam algısı oluşmuş | O kanalda dur, tonu gözden geçir, özür dile |

---

## 12. RİSKLER VE ÖNLEMLER

| # | Risk | Olasılık | Etki | Önlem |
|---|---|---|---|---|
| R1 | **Veri kaynağı kırılması** (bir markanın sitesi/API'si değişir, fiyatlar bayatlar) | Yüksek | Kritik — ürün vaadi çöker | Mevcut bayatlık (staleness) mekanizması zaten yanlış fiyatı gizliyor. **Pazarlama tarafı:** bir marka verisi bozulursa sosyal medyada **önce biz duyururuz** ("X markası verisinde geçici sorun var, çalışıyoruz"). Şeffaflık, sessizlikten daha az zarar verir. |
| R2 | **Marka itirazı / hukuki temas** (fiyat verisi kullanımı, logo, marka adı) | Orta | Yüksek | Logo kullanılmaz. Marka adları yalnızca tanımlayıcı bağlamda geçer. Fiyatlar kamuya açık kaynaklardan, atıfla. İletişimde hiçbir markaya olumsuz gönderme yapılmaz. Bir itiraz gelirse tartışmaya girilmez, hızlı ve nazik yanıt verilir. |
| R3 | **Play politika ihlali** (yanıltıcı store metni, sahte yorum, izin gerekçesi) | Düşük | Kritik — uygulama kaldırılır | §4.3 yasak mesaj listesine uyulur. Yorum manipülasyonu asla yapılmaz. Konum izni gerekçesi store'da açıkça yazılır. Data Safety beyanı gerçeği yansıtır. |
| R4 | **Tek kişilik ekip tükenmişliği** | **Yüksek** | Yüksek — plan durur | Haftalık 8-10 saat sınırı aşılmaz. İçerik **toplu üretilir** (ayda bir gün, 12 video). Şablon kullanımı zorunludur. Bir hafta atlanırsa plan çöpe atılmaz, kaldığı yerden devam eder. |
| R5 | Viral içeriğin gelmemesi | Yüksek | Orta | Viral içerik hedef değil, yan üründür. Plan **tutarlılık** üzerine kuruludur: 40 içeriğin 2'si tutar, o 2'si dönemin işini görür. |
| R6 | Zam bilgisinin yanlış paylaşılması | Orta | **Yüksek — otorite kaybı** | Zam, **iki bağımsız kaynaktan** doğrulanmadan paylaşılmaz. Yanlış paylaşım olursa 15 dakika içinde açık düzeltme yapılır. |
| R7 | Topluluklarda spam algısı → ban | Orta | Orta | §7.3 etik kuralları. Kanal başına frekans sınırı. Kimlik gizlenmez. |
| R8 | Rakiplerin akıllı skoru kopyalaması | Orta | Orta | Zaman avantajı kullanılır: konumlandırmayı **önce biz sahipleniriz**. Kategori kelimesi hâline gelen ifade ("en mantıklı istasyon") kopyalayanı bize benzetir. |
| R9 | Kullanıcı büyürken altyapı maliyeti (Maps API, Supabase) | Orta | Yüksek | 30K MAU eşiğinde maliyet projeksiyonu yapılır; Faz 1/2 gelir kararının tetikleyicisi budur. **Maliyet gelirden önce gelirse büyüme değil kriz olur** — W13 kontrolü bu yüzden var. |

---

## 13. EKLER — KULLANIMA HAZIR METİNLER

### Ek A — Google Play uzun açıklama metni

> Aşağıdaki metin doğrudan Play Console → Store listing → Full description alanına
> yapıştırılabilir. Karakter sayısı ~2.750 (sınır: 4.000).

```text
En ucuz istasyon her zaman en kârlı istasyon değildir.

Fullet, yakınındaki akaryakıt fiyatlarını tek haritada gösterir — ama orada
durmaz. Aracının tank kapasitesini, ortalama tüketimini ve o istasyona gitmenin
maliyetini de hesaba katarak sana gerçekten kâr eden istasyonu söyler.

⛽ TÜRKİYE GENELİNDE 6.000'DEN FAZLA İSTASYON
Shell, Opet, Petrol Ofisi, BP, TotalEnergies, Türkiye Petrolleri ve Aytemiz
istasyonlarının güncel akaryakıt fiyatları tek haritada. Benzin, motorin, LPG
ve elektrik için ayrı ayrı filtrele.

🧠 AKILLI SEÇİM — "EN UCUZ" DEĞİL, "EN MANTIKLI"
3 km öteye gidip litrede 40 kuruş kazanmak gerçekten kâr mı? Fullet bu hesabı
senin için yapar. Garajına aracını ekle; harita artık senin aracına göre çalışsın.

🔍 FİYATIN KAYNAĞI AÇIKÇA YAZIYOR
Türkiye'de akaryakıt fiyatları çoğunlukla il bazında ilan edilir. Bu yüzden
Fullet her fiyatın kapsamını gösterir: "Ankara geneli ilan fiyatı" mı, yoksa
"İstasyondan doğrulandı" mı? Ve en önemlisi: doğrulayamadığımız bir fiyatı
sana hiç göstermeyiz. Eksik bilgi, yanlış bilgiden iyidir.

💰 BU DEPO SANA KAÇA PATLAR?
Depo doldurma tahmini: tank kapasiten × litre fiyatı + istasyona gitme maliyeti.
Tahmin değil, hesap.

📈 FİYAT GEÇMİŞİ VE TREND
Bu istasyonda fiyat yükseliyor mu, düşüyor mu? Son değişimleri gör, kararını
ona göre ver.

🚗 SÜRÜŞ MODU
Yoldayken telefona bakmadan en yakın ve en mantıklı istasyonu gör, tek dokunuşla
yol tarifi al.

⭐ FAVORİLER VE ARAMA
Sürekli gittiğin istasyonları favorine ekle, tüm istasyonlar arasında arama yap.

🌙 GECE MODU
Gece sürüşünde göz yormayan koyu harita teması.

🔔 HATIRLATMALAR
Depo döngün geldiğinde ve fiyatlar hareketlendiğinde haberin olsun.

NASIL ÇALIŞIYOR?
Fullet fiyatları hazır bir listeden almaz. Her marka için ayrı veri toplama
sistemimiz, markaların kendi resmi kaynaklarından günde 4 kez fiyat toplar.
Bir fiyat uzun süre güncellenmezse önce "eski" olarak işaretlenir, sonra
gizlenir. Sana yanlış istasyonu göstermemek, çok istasyon göstermekten
daha önemli.

Ücretsiz. Hesap açmadan kullanabilirsin. Giriş yapmak sadece favorilerini
cihazlar arasında senkronlamak için gerekir.

Yakıt fiyatları, benzin fiyatları, motorin fiyatı, mazot fiyatı, LPG fiyatları
ve en yakın benzin istasyonu araman gereken her an Fullet yanında.

Desteklenen markalar: Shell, Opet, Petrol Ofisi, BP, TotalEnergies,
Türkiye Petrolleri (TP), Aytemiz.
```

### Ek B — Sosyal medya bio metinleri

**X (Twitter) — 160 karakter**
```text
Akaryakıt fiyatlarını haritada karşılaştıran uygulama. En ucuz değil, en mantıklı
istasyonu gösteririz. Zam ve indirim haberleri burada. ⛽📍
```

**Instagram — 150 karakter**
```text
⛽ Türkiye'nin akaryakıt haritası
🧠 En ucuz değil, EN MANTIKLI istasyon
📊 Zam/indirim haberleri
📍 6.000+ istasyon · 7 marka
👇 Ücretsiz indir
```

**TikTok — 80 karakter**
```text
Yakıt fiyatları + gerçek maliyet hesabı. En ucuz değil, en mantıklı istasyon ⛽
```

**YouTube kanal açıklaması**
```text
Fullet, Türkiye genelindeki akaryakıt fiyatlarını haritada karşılaştıran ücretsiz
bir uygulamadır. Litre fiyatının yanı sıra aracınızın tüketimini ve istasyona gitme
maliyetini de hesaba katarak en kârlı istasyonu gösterir. Bu kanalda akaryakıt
fiyatları, zam/indirim analizleri ve yakıt tasarrufu içerikleri paylaşıyoruz.
```

### Ek C — Topluluk/forum ilk mesaj şablonu

> Reddit / forum / Facebook grubu için. **Grubun kurallarına göre uyarlanır ve
> uygulama adı ilk paragrafta geçmez.**

```text
Merhaba,

Yakıt fiyatlarını takip ederken hep aynı soruyla karşılaşıyordum: "Şu istasyon
40 kuruş ucuz ama 4 km uzakta — gitmeye değer mi?" Kimse bunu hesaplamıyordu.

Ben de kendim için bir şey yaptım, sonra herkese açtım. Uygulama Türkiye'deki
7 markanın (Shell, Opet, PO, BP, Total, TP, Aytemiz) fiyatlarını günde 4 kez
kendi topladığım verilerle haritaya basıyor. Farkı şu: aracının tank kapasitesi
ve tüketimini girince, o istasyona gitme maliyetini de hesaba katıp gerçekten
kâr eden istasyonu gösteriyor.

Dürüst olmak gerekirse eksikleri de var:
- Fiyatlar anlık değil, günde 4 kez güncelleniyor.
- Türkiye'de fiyatlar çoğunlukla il bazında ilan ediliyor; bu yüzden her fiyatın
  yanında kapsamını yazıyorum ("Ankara geneli ilan fiyatı" gibi). Doğrulayamadığım
  fiyatı hiç göstermiyorum — eksik göstermeyi yanlış göstermeye tercih ettim.
- Bazı bölgelerde istasyon kapsamı hâlâ zayıf.

Geri bildirime çok açığım, özellikle eksik/yanlış gördüğünüz istasyonlar için.
Buradaki her yoruma cevap vereceğim.

[Uygulama adı ve link — grup kuralları izin veriyorsa]
```

### Ek D — Basın / mikro-influencer e-posta şablonu

> Konu satırı kısa ve merak uyandırıcı olmalı. E-posta 150 kelimeyi geçmemeli.

```text
Konu: Aynı ilde iki istasyon arasında litrede 1,10 TL fark var — verisi bende

Merhaba [İsim],

[Kanal/site adı]'nda yakıt ve otomotiv maliyetleri üzerine yaptığınız içerikleri
takip ediyorum. Elimde ilginizi çekebilecek bir veri seti var.

Fullet adında bir akaryakıt fiyat uygulaması geliştirdim. Türkiye'deki 7 markanın
fiyatlarını günde 4 kez kendi sistemlerimle topluyorum — 6.000'den fazla istasyon.
Bu, Türkiye'de bağımsız olarak tutulan en ayrıntılı fiyat zaman serilerinden biri.

Verinin gösterdiği birkaç şey:
• [İl] içinde aynı gün, aynı yakıtta iki istasyon arasında litrede X TL fark
• Zam öncesi ve sonrası doldurma maliyeti farkı: 60 litrelik depoda Y TL
• [İlginç bir bulgu daha]

İçerik yapmak isterseniz veriyi, grafikleri ve ekran görüntülerini ücretsiz
paylaşırım — herhangi bir karşılık beklemiyorum, sadece kaynak gösterilmesi
yeterli. İsterseniz uygulamayı 5 dakikada anlatan kısa bir video da gönderebilirim.

İyi çalışmalar,
[İsim] — Fullet geliştiricisi
[E-posta] · [Play linki]
```

### Ek E — Zam gecesi hazır metin şablonları

**T-6 saat (X + Story)**
```text
🔴 ZAM UYARISI

Bu gece 00:00'dan itibaren [yakıt] litre fiyatına [X] TL zam bekleniyor.

Bu ne demek?
• 50 litrelik depo → +[A] TL
• 60 litrelik depo → +[B] TL
• 80 litrelik depo → +[C] TL

Deponuz boşsa bugün doldurmak mantıklı.
Yakınındaki güncel fiyatlar 👉 [link]
```

**T-0 (zam yürürlükte)**
```text
Yeni fiyatlar haritada. ⛽

[Yakıt] artık [il] genelinde [fiyat] TL.
Yakınındaki en mantıklı istasyonu görmek için 👉 [link]

(Fiyatları günde 4 kez markaların resmi kaynaklarından topluyoruz.
Doğrulayamadığımız fiyatı göstermiyoruz.)
```

**İndirim (daha az rekabet, daha çok paylaşılır)**
```text
🟢 İYİ HABER

[Yakıt] fiyatında [X] TL indirim.
60 litrelik depoda [Y] TL cebinde kalıyor.

Acele etmene gerek yok — ama nerede en ucuz olduğunu bilmek işine yarar 👉 [link]
```

### Ek F — Haftalık içerik takvimi şablonu (kopyala-kullan)

| Hafta: ___ | Pzt | Sal | Çar | Per | Cum | Cmt | Paz |
|---|---|---|---|---|---|---|---|
| **X** | Haftalık özet | Veri kartı | Soru-cevap | İl karşılaştırma | Yol tavsiyesi | — | Haftaya bakış |
| **Video** (TikTok+Reels+Shorts) | — | **Video 1**<br>Pilar: ___ | — | **Video 2**<br>Pilar: ___ | — | **Video 3**<br>Pilar: ___ | — |
| **Story** | Anket | Video tanıtımı | Kullanıcı mesajı | — | Anket sonucu | — | — |
| **Topluluk** | 2 grup gönderisi | — | Forum yanıtı | — | 2 grup gönderisi | — | — |
| **Play** | Yorumlara yanıt | — | — | Yorumlara yanıt | — | — | — |
| **Zam?** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

---

## KAPANIŞ — BU PLANIN TEK CÜMLESİ

> **Fullet'in büyümesi, para değil tutarlılık gerektiriyor: haftada üç video, günde
> bir gönderi, her zam gecesi ilk sen — ve doğrulamadığın hiçbir fiyatı asla
> paylaşmamak.**

Sıfır bütçeyle yüz binlerce kullanıcıya ulaşmanın kestirme yolu yoktur; ama
tekrarlanabilir bir yolu vardır. Bu belge o yoldur. 13 hafta boyunca uygulanır,
ölçülür ve her ay sonunda işe yaramayan kısımlar acımasızca kesilir.

---

*Bu belge yaşayan bir dokümandır. Her ay sonunda §11.5 analizine göre güncellenmelidir.*
*Vergi ve hukuk konularındaki notlar bilgilendirme amaçlıdır; mali müşavir ve hukuk
danışmanı görüşünün yerine geçmez.*
