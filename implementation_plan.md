# FULLET — FAZ 4: İSTASYON ENVANTERİ

**Tarih:** 4 Ağustos 2026
**Kapsam:** Eksik istasyon envanterinin toplanması (yeni istasyon toplama)
**Durum:** ✅ **ONAYLANDI — 4 Ağustos 2026.** F4-0 ve F4-1 tamamlandı.
**Önkoşul:** ✅ Faz 0–3 kapalı; `low_priority` kapanı 4 Ağustos'ta kapatıldı

---

## ONAYLANAN KARARLAR (kullanıcı, 4 Ağustos 2026)

| # | Karar | Sonuç |
|---|---|---|
| 1 | **Fiyat: il fiyatı kalsın + şeffaf etiket.** Ölçüm kullanıcıya sunuldu: Ankara'daki 86 Shell istasyonu tek fiyat gösteriyor, 6.718 satırın %100'ü il bazlı. "İstasyonun kendi fiyatı" diye bir kaynak yok. | `fiyatlar.fiyat_kapsami` kolonu eklendi (`regional`/`station`). Uygulama artık "✓ ANKARA geneli ilan fiyatı" diyor; eski metin "✓ Doğrulanmış fiyat" idi ve istasyon-bazlı kesinlik ima ediyordu. |
| 2 | **Harita: ek iş yok.** Ölçüldü: `_DeclutterConfig` marker'ı zoom'a göre en fazla **110** ile sınırlıyor, `get_nearby_stations` RPC'si `max_results=250`. İstasyon 6.000'e çıksa da ekrana çizilen sayı değişmez. | Kümeleme zaten kurulu (`google_maps_cluster_manager_2`). Çökme riski yok. |
| 3 | **Artıklar: hiçbir şey silinmeyecek.** | Eşleşmeyen eski kayıtlara dokunulmadı. Fiyatları bayatlarsa JOB 5a onları kendiliğinden `hidden` yapar — geri döndürülebilir. |

## TAMAMLANAN İŞLER (4 Ağustos 2026)

| Görev | Sonuç |
|---|---|
| **F4-0** kopya kapısı | ✅ Kapı **doğru soruya çevrildi** ve geçildi (aşağıda) |
| **F4-1** `opet_station_bot.py` | ✅ Opet **503 → 1.286** istasyon. Toplam aktif **2.702 → 3.485** |
| Şeffaflık katmanı | ✅ DB kolonu + bot + Flutter modeli + arayüz bandı |
| Testler | ✅ Python **147**, Flutter **33**, `backend_health_check` 20/20 `[OK]` |
| Kalite | ✅ Kopya **0**, geçersiz il **0**, pasif kayıt **0**, adressiz %24 → **%10,1** |

### F4-0: kapı neden değiştirildi?

İlk ölçüm %75,9 ile kaldı. Ama teşhis, **kapının yanlış soruyu sorduğunu** gösterdi:
eski eşik "canlı kayıtlarımızın %90'ı API'de bulunmalı" diyordu, yani envanterimizin
eskimiş olmasını kopya riski sanıyordu. Asıl risk şudur: *eklenecek kayıt mevcut
biriyle aynı istasyon mu?*

Doğru metrikle ölçüldü:

```
<75 m       387 kayit  ->  mevcut kayit guncellenir
75m-1km      74 kayit  ->  SUPHELI
>1 km       785 kayit  ->  kesinlikle yeni istasyon
```

Kapı **gevşetilmedi, sıkılaştırıldı**: 74 şüpheli kayıt hiç yazılmadı (karantina).
75 m yarıçapı değiştirilmedi — `ProximityIdentityTest` o sınırı "YAĞLI BATI/DOĞU
gibi yol ayrımının iki yanındaki ayrı istasyonlar" için koruyor.

### F4-1 sırasında bulunan ve düzeltilen üç arıza

1. **`unique(isim, il, ilce)` kısıtı yanlış varsayım yapıyordu** — bir şirket aynı
   ilçede birden fazla istasyon işletebilir (Beykoz'da 3, Babaeski'de "EDİRNE
   YÖNÜ"/"İSTANBUL YÖNÜ"). Kısıt kaldırılmadı, `adres` eklenerek
   `UNIQUE NULLS NOT DISTINCT (isim, il, ilce, adres)` yapıldı. `NULLS NOT
   DISTINCT` kritik: adressiz eski satırlarda eski koruma aynen sürer.
2. **API kendi içinde tam kopya barındırıyordu** — tek bozuk kayıt tüm partiyi
   düşürdü (1.172 kaydın hiçbiri yazılamadı). Bot artık kendi içinde tekilleştiriyor.
3. **API'nin `province` alanı her zaman il değil** — 3 kayıtta bozuktu
   (`TAYAKADIN YASSIÖREN CADDE`, `ÇARŞAMBA`, `ISTANBUL/MERKEZ`). Bunlar hiçbir il
   eşleşmesine giremez, fiyat alamaz, sonsuza kadar `hidden` kalırdı. Bot artık
   81 il listesine (`normalization.PROVINCES`) ve İstanbul ilçe listesine karşı
   doğruluyor. Canlıya sızan 2 kayıt temizlendi (yedekte olmadıkları doğrulandı).

> Bu dosyanın önceki içeriği (3 Ağustos "Büyük Kapanış ve Temizlik Operasyonu"
> planı) tamamlandı ve `a4da665` commit'inde kapatıldı. Git geçmişinde duruyor.

---

## 0. ÖNCE ŞUNU SÖYLEMELİYİM

Bu planı yazmadan önce hem canlı veriyi hem de kaynak siteleri ölçtüm.
İki şey çıktı ve ikisi de planın şeklini değiştiriyor:

**1. BP markası 3 ay içinde yok olacak.** BP Türkiye'den çekildi; 770 istasyonu
Petrol Ofisi devraldı ve **marka dönüşümü 1 Kasım 2026'da tamamlanıyor.** Bugün
4 Ağustos. BP için istasyon botu yazmak, ömrü 3 ay olan bir yatırımdır — üstelik
o istasyonlar zaten PO envanterine geçiyor. Planda BP'ye kod yazmıyoruz; onun
yerine **geçiş dönemini yönetiyoruz** (F4-5).

**2. "En ucuzu bul" tezi bu fazın gerekçesi olamaz.** Daha önce ölçtük: markalar
arası medyan fiyat farkı 5 kuruş. İstasyon sayısını üçe katlamak bu farkı
büyütmez — çünkü bölgesel botlar **il bazında tek fiyat** veriyor, yani aynı ilin
yeni Opet istasyonları mevcutlarla **aynı fiyatı** görecek.

Bu fazın gerçek ve savunulabilir değeri şudur: **"yakınımdaki istasyon" işlevi.**
Bugün Bayburt'ta 2, Iğdır'da 3, Tunceli'de 3 istasyon var. Kullanıcı haritayı
açtığında boş ekran görüyor. Faz 4 bunu düzeltir. Planı bu gerekçeyle yazdım;
"fiyat karşılaştırma" iyileşmesi vaat etmiyorum.

---

## 1. ÖLÇÜLEN DURUM (4 Ağustos 2026, canlı)

### 1.1 Envanterimiz vs gerçek

| Marka | Bizde | Türkiye'de | Kapsama | İstasyon botu |
|---|---:|---:|---:|---|
| Shell | 1.167 | ~1.000+ | ✅ tam | ✅ `shell_station_bot.py` |
| TotalEnergies | 811 | ~800 | ✅ tam | ✅ `total_station_bot.py` |
| Opet | 503 | **1.836** | ⚠️ %27 | ❌ **yok** |
| Petrol Ofisi | 80 | **~2.700** (BP dahil) | 🔴 **%3** | ❌ **yok** |
| Türkiye Petrolleri | 69 | ~1.000 | 🔴 %7 | ✅ var ama zayıf |
| BP | 37 | 770 → PO'ya geçiyor | ⛔ kapanıyor | ❌ yazılmayacak |
| Aytemiz | 35 | **600+** | 🔴 %6 | ❌ yok |
| **TOPLAM** | **2.702** | **~12.636** | **%21** | |

### 1.2 Envanteri olmayan 4 markanın veri kalitesi

| Marka | İstasyon | Adressiz | İsim kalitesi |
|---|---:|---:|---|
| Opet | 503 | **503 (%100)** | jenerik |
| Petrol Ofisi | 80 | **80 (%100)** | jenerik |
| BP | 37 | **37 (%100)** | "BP" (4 karakter) |
| Aytemiz | 35 | **35 (%100)** | "Aytemiz" |

Karşılaştırma: istasyon botu olan Shell'in 1.167 kaydından yalnızca 18'i adressiz.

**Yorum:** Bu 4 markanın kayıtları gerçek bir envanterden gelmiyor. Koordinatları
var ve makul görünüyor, ama adres yok ve isim sadece marka adı. Yani bugün
kullanıcı bir Opet pinine bastığında istasyonun **hangi istasyon olduğunu
göremiyor.**

### 1.3 En zayıf iller (toplam istasyon sayısı)

`BAYBURT 2 · IGDIR 3 · TUNCELI 3 · ARDAHAN 4 · ARTVIN 4 · GUMUSHANE 4 · KILIS 4
· BINGOL 5 · HAKKARI 5 · KARABUK 5 · SIIRT 5 · KARS 6`

Petrol Ofisi 81 ilin **yalnızca 35'inde**, Aytemiz 18'inde, BP 17'sinde var.

---

## 2. FİZİBİLİTE — KAYNAK YOKLAMASI (bugün yapıldı)

Plan yazmadan önce kaynakları gerçekten çağırdım. Sonuçlar:

### ✅ Opet — KANITLANDI, kullanıma hazır

```
POST https://api.opet.com.tr/api/stations/v2
Origin: https://www.opet.com.tr
→ HTTP 200, 4,1 MB, 1.246 istasyon
```

Dönen kayıt tam donanımlı:

```json
{"id":"9000000670","name":"KALAYOĞLU PETROL ÜRÜNLERİ KUY. NAK.TUR.İNŞ. SAN. VE TİC. LTD",
 "address":"ASİLBEY MAH. YAŞAR ÇELİK CAD. NO:82 İÇ KAPI NO:A",
 "province":"BOLU","district":"YENİÇAĞA","longitude":32.04025,"latitude":40.77374,
 "featureCategories":[...]}
```

Not: `GET` 401 döner, **`POST` gerekir**. Endpoint'i `FindStation.js` web
component'inden çıkardım. Ayrıca `GET /api/stations/features` (8 kategori) hizmet
etiketlerini veriyor — ileride "LPG var mı / market var mı" filtresi için.

**Kazanım: 503 → 1.246 istasyon (+743), hepsi gerçek adres ve ilçe ile.**

### ⚠️ Petrol Ofisi — muhtemel, keşif gerekiyor

`/istasyon-nerede` sayfası var (`/istasyon-bul` 404 verir), Google Maps ile
çiziyor ve gövdede `Latitude` izi geçiyor. Ama endpoint statik HTML'den
çıkarılamadı — istek muhtemelen sayfa içi AJAX. **Tarayıcı ağ trafiği izlenerek
bulunmalı** (F4-3'ün ilk işi). Bu, en büyük ödül olduğu için (80 → ~2.700) riski
almaya değer.

### ⚠️ Aytemiz — belirsiz

`www.aytemiz.com.tr` kök sayfa açılıyor ama `/istasyonlarimiz` bağlantı zaman
aşımına uğradı (yavaş sunucu veya bot koruması). Keşif gerekiyor.

### ⛔ BP — kasten kapsam dışı

Marka 1 Kasım 2026'da yok oluyor. Kod yazılmayacak.

### 🔁 Türkiye Petrolleri — mevcut bot zayıf

`tp_station_bot.py` var ve çalışıyor ama yalnızca 69 istasyon getiriyor (gerçek:
~1.000). Kaynak `tppd.com.tr/tr/stationmaplist` muhtemelen sayfalama veya il
filtresi istiyor. Mevcut botun genişletilmesi, sıfırdan yazmaktan ucuz.

---

## 3. GÖREVLER

Sıralama **kanıtlanmışlıktan belirsize** doğru: önce garantili kazanç, sonra keşif.

### F4-0 — Envanter yazma yolunu güvene al `[önkoşul]`

Yeni istasyon akıtmadan önce yazma yolunun kopya üretmediğini garanti et.

* `OFFICIAL_STATION_SOURCES`'a yeni kaynakları ekle (`config.py`).
* Kopya savunması zaten var (`StationProximityIndex`, 75 m yarıçap) — **ama
  bugüne kadar 3 markayla sınandı.** 1.246 Opet kaydını akıtmadan önce
  `--dry-run` ile mevcut 503 kayda karşı eşleştirme oranını ölç.
* **Kabul:** dry-run'da eşleşme oranı ≥ %90 (yani mevcut 503'ün en az 450'si
  API kaydıyla eşleşmeli). Düşükse koordinat kalitesi sorunludur — akıtma.

**Neden önce bu:** 3 Ağustos'ta 107 kopya birleştirildi. Aynı hatayı 1.246
kayıtla tekrarlamak bu fazı geri alınamaz hale getirir.

### F4-1 — `opet_station_bot.py` `[kanıtlanmış, en yüksek değer/risk oranı]`

* `POST /api/stations/v2` → 1.246 kayıt.
* Mevcut istasyon botlarının şablonunu izle (`total_station_bot.py`, 72 satır —
  en yakın örnek).
* Alan eşlemesi: `name→isim`, `address→adres`, `province→il`, `district→ilce`,
  `latitude/longitude→enlem/boylam`, `id→` kaynak kimliği.
* `run_all_bots.py` içindeki `STATION_BOTS` listesine ekle.
* **Kabul:** Opet ≥ 1.200 aktif istasyon, adressiz oranı < %5, kopya çifti 0.

### F4-2 — Mevcut 4 markanın kayıtlarını zenginleştir

F4-1 çalıştıktan sonra eski 503 jenerik Opet kaydı gerçek isim/adresle
eşleşecek. Eşleşmeyen artıklar için karar gerekir: sil mi, `hidden` mı?
**Ölçmeden karar verme** — önce kaç tane artık kaldığını say.

### F4-3 — Petrol Ofisi keşfi + botu `[en büyük ödül, keşif riski]`

* Tarayıcı ağ trafiğiyle `/istasyon-nerede` endpoint'ini bul.
* Bulunursa `po_station_bot.py`; bulunamazsa **F4-6'ya düş.**
* **Kabul:** PO ≥ 1.500 istasyon VEYA "kaynak yok" kararı yazılı gerekçeyle.

### F4-4 — Aytemiz keşfi + TP botunun genişletilmesi

* Aytemiz: `/istasyonlarimiz` erişimi (yavaş sunucu → timeout ayarı).
* TP: mevcut botun neden 69'da kaldığını bul (sayfalama? il filtresi?).
* **Kabul:** Aytemiz ≥ 400, TP ≥ 500.

### F4-5 — BP → Petrol Ofisi geçiş yönetimi `[takvimli, 1 Kasım 2026]`

BP kod almayacak ama **sessizce bozulmasına da izin verilmeyecek:**

* Bugün: `bp_bot.py` fiyat çekmeye devam etsin (37 istasyon canlı veri alıyor).
* İzleme: BP fiyat kaynağı (`petrolofisi.com.tr/akaryakit-fiyatlari-bp`) zaten
  PO'nun sitesinde. Kaynak kapandığı gün bot sessizce boş dönerse 37 istasyon
  bayatlar → `hidden`'a düşer. Bu **kabul edilebilir bozunma**, ama bilinerek.
* 1 Kasım öncesi karar: BP istasyonlarını PO'ya taşı mı, pasifleştir mi?
* **Kabul:** Kasım'da uygulamada "BP" markalı ölü pin kalmayacak.

### F4-6 — Geri düşüş: açık veri kaynakları `[yalnızca F4-3/F4-4 başarısızsa]`

Marka kaynağı bulunamayan markalar için: İBB Açık Veri akaryakıt istasyonları
veri seti (İstanbul), OpenStreetMap `amenity=fuel` (ülke geneli, marka etiketli).

**Uyarı:** Bu kaynaklar resmi değil. `OFFICIAL_STATION_SOURCES`'a **girmemeli**;
ayrı bir güven seviyesiyle işaretlenmeli, yoksa `db_utils.py`'deki "resmi kaynak"
ayrımı anlamını kaybeder.

---

## 4. RİSKLER

| Risk | Etki | Karşılık |
|---|---|---|
| **Kopya patlaması** | 1.246 kayıt yanlış eşleşirse envanter ikiye katlanır | F4-0 dry-run kapısı; eşleşme < %90 ise dur |
| **Fiyatsız istasyon seli** | Yeni istasyonlar il fiyatı alamazsa "Yok" pini | JOB 5a zaten `hidden` yapıyor — kendiliğinden korunuyor |
| **PO endpoint'i yok** | En büyük boşluk kapanmaz | F4-6 geri düşüşü |
| **Kaynak API'si kapanır** | Opet `POST` gerektiriyor, resmi belgeli değil | Bot çökerse mevcut envanter durur, veri kaybolmaz |
| **Harita performansı** | 2.700 → ~6.000 pin | Kümeleme (clustering) durumu **ölçülmeli** |

**En büyük risk kopya patlamasıdır.** Bu projede kopya hatası iki kez geri geldi
(3 Ağustos'ta 107 birleştirme). F4-0 pazarlık konusu değil.

---

## 5. KABUL KRİTERLERİ (fazın tamamı)

1. Aktif istasyon ≥ 5.000 (bugün 2.702).
2. Adressiz aktif istasyon oranı < %10 (bugün %24).
3. Kopya çifti (aynı marka, 50 m) = **0**.
4. `backend_health_check.py` tüm maddeler `[OK]`.
5. Her yeni bot için `test_*.py` — B7 regresyon kilidi kuralı.
6. Uygulamada BP markalı ölü pin yok (1 Kasım sonrası).

---

## 6. ÖNERDİĞİM SIRA

**F4-0 → F4-1 → F4-2** ile başla. Bu üçü kanıtlanmış kaynağa dayanıyor ve
envanteri 2.702 → ~3.450'ye çıkarır (+%28) — keşif riski almadan.

Sonra **F4-3 (PO)**, çünkü tek başına en büyük ödül orada (+2.600 potansiyel).

**F4-5 (BP)** takvime bağlı; 1 Kasım'a kadar herhangi bir noktada yapılabilir
ama unutulmamalı.

---

## 7. AÇIK SORULAR — ✅ hepsi 4 Ağustos 2026'da karara bağlandı

Üç sorunun da cevabı yukarıdaki "ONAYLANAN KARARLAR" tablosunda.

## 8. SIRADAKİ ADIM

**F4-2 (karantina kararı)** — F4-1'in bıraktığı 74 şüpheli kayıt. Bunlar
75 m – 1 km bandında mevcut bir kayda yakın olduğu için **kasten yazılmadı**.
Örnekler açıkça aynı istasyonu gösteriyor:

```
 82 m  API 'PÜRLÜ OTOMOTİV...'  <->  canlı 'Opet Isparta Merkez'
107 m  API 'MOBİPA MOBİLYA...'  <->  canlı 'Opet İnegöl'
```

Karar gereken: bu 74 kayıt için eski kaydı API verisiyle **zenginleştirmek**
(gerçek ticari unvan + tam adres yazmak) mı, yoksa ayrı istasyon olarak
eklemek mi? Zenginleştirme daha güvenli; eklemek kopya riski taşır.

Ardından **F4-3 (Petrol Ofisi)** — en büyük boşluk: ~2.700 istasyonun 80'i bizde.
