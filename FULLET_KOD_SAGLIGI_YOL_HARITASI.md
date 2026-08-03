# FULLET — TAM KOD DENETİMİ VE DÜZELTME YOL HARİTASI

**Tarih:** 2 Ağustos 2026
**Kapsam:** Tüm depo — 30 Python dosyası, 27 Dart dosyası, admin panel (React), 25 SQL
dosyası, 2 Edge Function, 2 GitHub Actions workflow'u. Satır satır okundu.
**Amaç:** "Uygulama yanlış fiyat gösteriyor ve taze veri çekemiyor" şikâyetinin
koddaki her kaynağını bulmak ve düzeltme sırasını belirlemek.

---

## 0. YÖNETİCİ ÖZETİ

Şikâyet tek bir hatadan gelmiyor. **Dört bağımsız arıza zinciri** aynı anda çalışıyor ve
her biri diğerini gizliyor:

| # | Zincir | Sonuç |
|---|---|---|
| A | Botlar hatayı yutup `exit 0` dönüyor + CI'da alarm bayrağı kapalı | Kırık parser "başarılı" görünüyor |
| B | `son_guncelleme` kolonu iki farklı anlam taşıyor + eşikler çakışıyor | Fiyat doğruyken bile "bayat" oluyor |
| C | Sabit kolon indeksleri + çapraz doğrulama kapısı yok | Yanlış fiyat sessizce yazılıyor (Shell LPG) |
| D | Uygulamada yakıt filtresi ölü + tazelik göstergesi yanlış | Kullanıcı "Yok"/eski fiyat görüyor |

**En önemli tek cümle:** Bu sistemde hiçbir bileşen "veri kötü" diyemiyor. Bot 0 kayıt
yazınca `success`, panel 72 saati temiz sayarken uygulama 12 saati bayat sayıyor,
`ops_report` Shell alarmlarını körü körüne kapatıyor, `quarantine_old_prices.py` hiç
çalışmıyor. Gözlem katmanı yalan söylediği için 4 marka aylardır sessizce ölü.

Toplam **26 doğrulanmış bulgu**. Aşağıda önem sırasına göre, sonra düzeltme sırası.

---

## 1. BULGULAR

### S0 — SİSTEMİK KÖK NEDENLER
*(Tek düzeltme, çok belirti kapatır. Diğer her şeyden önce bunlar.)*

---

#### S0-1 — Her fiyat botu istisnayı yutup başarıyla çıkıyor
**Dosyalar:** `scraper/opet_bot.py:56`, `po_bot.py:60`, `bp_bot.py:60`,
`aytemiz_bot.py:66`, `tp_bot.py:118`, `total_bot.py:65`, `shell_bot.py:207`,
`shell_station_bot.py:175`, `total_station_bot.py:60`, `tp_station_bot.py:46`

Her botun kalıbı aynı:

```python
except Exception as exc:
    print(f"[WARN] Opet scrape failed: {exc}")
return scraped_data          # ← boş liste

if __name__ == "__main__":
    data = scrape_opet_data()
    save_to_supabase(data, default_brand="Opet")   # 0 kayıt yazar
    print("[OK] Opet finished")                     # exit code 0
```

Site şeması değişse, HTTP 500 dönse, JSON bozulsa — bot **`exit 0`** ile biter.
`run_all_bots._run_subprocess_once` yalnızca `returncode`'a bakar (satır 130), dolayısıyla
`bot_runs.status = 'success'`, `exit_code = 0` yazılır.

> Karar protokolündeki "7 markanın 4'ünde tek bir taze fiyat yok ama botlar `success`"
> gözleminin doğrudan mekanizması budur.

**İstisna:** `news_bot.py:131` — tek doğru davranan bot, `raise SystemExit(1)` yapıyor.
Diğerleri onu örnek almalı.

---

#### S0-2 — CI, tüm hata/alarm altyapısını kapatıyor
**Dosya:** `.github/workflows/otopilot.yml:159`

```yaml
FULLET_FAIL_ON_BOT_ERROR: "0"
```

Bu tek satır şunları etkisizleştiriyor:

- `run_all_bots.should_open_failure_alert()` → her zaman `False` → **hiçbir bot için
  `system_alerts` kaydı açılmıyor.**
- `run_all_bots.main()` → `failures` dolu olsa bile `return 0` (satır 256-259).
- Son commit'te eklenen retry + `TOLERATED_FAILURE_BOTS = set()` temizliği
  (satır 47, 170-177) **üretimde hiç çalışmıyor** — o kod yolu CI'da erişilemez.

Geriye tek alarm yolu kalıyor: `telemetry._check_consecutive_failures`. O da S3-2'deki
hata yüzünden güvenilmez.

---

#### S0-3 — `son_guncelleme` iki farklı anlam taşıyor; eşikler birbirini yiyor
**Dosyalar:** `scraper/database_writes.py:66-80`, `database/auto_price_staleness.sql:27-36`,
`database/production_hardening.sql:309-338`

Üç yer aynı kolona farklı anlam yüklüyor:

1. **Trigger** (`log_fiyat_degisimi`, BEFORE UPDATE): `son_guncelleme`'yi yalnızca
   **fiyat değerinin değiştiği** anda `NOW()` yapıyor → "son değişim zamanı".
2. **pg_cron JOB 1**: `son_guncelleme < NOW() - 12 hours` ise `fresh → stale` →
   "son doğrulama zamanı" varsayıyor.
3. **Bot diff'i** (`_bulk_upsert_prices`): fiyat aynı + status `fresh` + yaş **< 24 saat**
   ise satırı tamamen atlıyor → `son_guncelleme` **bump edilmiyor.**

Sonuç, Türkiye'de fiyatların ayda birkaç kez değiştiği gerçeğiyle birleşince:

```
T+0h   bot yazar        → fresh,  son_guncelleme = T0
T+6h   bot koşar        → fiyat aynı, fresh, yaş 6h < 24h → ATLA (bump yok)
T+12h  cron             → stale                              ← fiyat DOĞRU ama bayat
T+18h  bot koşar        → status != fresh → yazar → fresh
T+24h  ...              → döngü tekrar
```

Fiyat hiç değişmese bile sistem sürekli `fresh → stale → fresh` salınıyor. Kullanıcı
gün içinde **doğru fiyatı "⚠️ Bayat fiyat" bandıyla** görüyor.

`scraper/test_backend_utils.py:226` (`test_zero_cost_unchanged_prices_skipped`) bu atlama
davranışını *istenen davranış* olarak test ediyor — optimizasyon fikri doğru, ama 24 saatlik
eşik 12 saatlik cron'la uyumsuz. **Asıl eksik, ayrı bir "son doğrulama" kolonu.**

---

#### S0-4 — Dört bileşen, dört farklı tazelik eşiği
| Bileşen | Dosya | Eşik |
|---|---|---|
| pg_cron `fresh→stale` | `auto_price_staleness.sql:34` | **12 saat** |
| pg_cron `stale→unknown` | `auto_price_staleness.sql:50` | **48 saat** |
| `quarantine_old_prices.py` | satır 42 | **72 saat** |
| `ops_report.py` | `MAX_PRICE_AGE_HOURS` satır 54 | **48 saat** |
| Admin panel | `admin_panel/src/App.jsx:16` | **72 saat** |
| `backend_health_check.py` (haber) | satır 25-26 | 24/48 saat |

Admin panel 72 saati "Temiz" gösterirken uygulama aynı fiyata "Bayat" diyor.
**"Panel yeşil, veri ölü" tablosunun ikinci yarısı budur.**

---

### S1 — YANLIŞ VERİ ÜRETENLER

---

#### S1-1 — Shell LPG sabit kolon hatası (HÂLÂ AÇIK)
**Dosya:** `scraper/shell_bot.py:128`

```python
"LPG": _price_at(cols, 12) or _price_at(cols, 10),
```

Son commit Shell'i tolere listesinden çıkardı ama **kolon hatası düzeltilmedi.**
Canlı veri: Shell LPG 37,74 TL, diğer markalar ~31,3 TL (%20 sapma, 860 kayıt).

Aynı fonksiyonda `Kursunsuz 95` ve `Motorin` de `or` fallback kullanıyor (satır 126-127) —
aynı sınıf hataya açık, şu an tesadüfen doğru okuyorlar.

---

#### S1-2 — Aynı sayfa, iki botta farklı kolon indeksleri
**Dosyalar:** `scraper/po_bot.py:44-48` vs `scraper/bp_bot.py:44-48`

Her ikisi de `petrolofisi.com.tr` üzerinde aynı tablo yapısını okuyor
(`soup.select("table tr")`), ama:

| | Kurşunsuz 95 | Motorin | LPG |
|---|---|---|---|
| `po_bot.py` | `cols[1]` | **`cols[2]`** | **`cols[6]`** |
| `bp_bot.py` | `cols[1]` | **`cols[3]`** | **`cols[8]`** |

İkisi aynı anda doğru olamaz. BP botu %19 taze veri üretirken PO botunun %0 üretmesi
bu tutarsızlıkla uyumlu. **Canlı sayfadan doğrulanmalı** — ama asıl çözüm sabit indeks
değil, başlık metnine göre kolon bulma (S1-4).

> ### ⚠️ DÜZELTME (2 Ağustos, Faz 1) — bu bulgu YANLIŞTI
>
> Canlı sayfalar çekildi. İki sayfa **farklı kolon sayısına** sahip ve her iki bot
> da kendi tablosu için **doğru** indeksleri kullanıyordu:
>
> ```
> PO: Şehir | V/Max Kurşunsuz 95 | V/Max Diesel | Gazyağı | Kalorifer | Fuel Oil | PO/gaz Otogaz
>            [1] ✓                 [2] ✓                                           [6] ✓
> BP: Şehir | BP Kurşunsuz | BP Ultimate | BP Diesel | BP Ultimate Diesel | ... | Otogaz | Y.K.Fuel Oil
>            [1] ✓                         [3] ✓                                 [8] ✓
> ```
>
> Aynı şekilde Aytemiz'in `price_start=6` sabiti ve TP'nin indeksleri de doğruydu.
> **Tek gerçek veri bozan kolon hatası Shell LPG'ydi (S1-1).**
>
> Yine de beşi de başlık tabanlı çözüme taşındı: sabit indeks doğru olsa bile
> kırılgandır — Shell'de tam olarak bu yüzden patladı.
>
> **Ders:** "İki bot aynı sayfayı farklı okuyor" çıkarımı, sayfaların aynı olduğu
> **varsayımına** dayanıyordu. Kaynağı görmeden yapılan çıkarım yanıltıcıydı;
> raporda "canlı doğrulanmalı" işareti bu yüzden konmuştu.

---

#### S1-3 — Aytemiz parser'ı sihirli sayılarla token yürüyor
**Dosya:** `scraper/aytemiz_bot.py:15-33`

```python
price_start = 6
index = price_start
while index + 5 < len(tokens):
    ...
    index += 6
```

Tablo düzeni değişirse (ki `veri_kaynagi` olarak bildirilen URL ile gerçekte
çekilen URL bile farklı — satır 42 `/benzin-fiyatlari`, satır 64 `akaryakit-fiyatlari`),
bu döngü sessizce yanlış hücreleri okur ya da hiç sonuç üretmez. Ayrıca
`index + 5 < len(tokens)` koşulu **son satırı her zaman düşürüyor.**

---

#### S1-4 — Çapraz doğrulama kapısı yok; fiyat aralığı çok geniş
**Dosyalar:** `scraper/normalization.py:88,111`, `scraper/backend_health_check.py:229-231`

`parse_price` `0 < price < 300` kabul ediyor. LPG ~31, motorin ~82 olan bir pazarda
bu, kolon kayması sonucu okunan neredeyse her sayıyı geçerli sayar. Shell LPG'nin 37,74
olarak yazılması tam olarak buradan geçti.

`backend_health_check.py` daha dar bir aralık (5–200) kullanıyor ama o da 37,74'ü yakalayamaz.
**Hiçbir yerde "bu markanın bu yakıttaki medyanı, diğer markaların medyanından ne kadar
sapıyor" kontrolü yok.** Tek satırlık bu kural hatayı ilk gün yakalardı.

---

#### S1-5 — `quarantine_old_prices.py` üretimde hiç çalışmıyor
**Dosya:** `scraper/run_all_bots.py:247-251`

```python
subprocess.run(
    [sys.executable, str(SCRAPER_DIR / "quarantine_old_prices.py")],
    cwd=SCRAPER_DIR,
    env=bot_env,          # ← bot_env = {"FULLET_PUSH_SUMMARY": "0"}
)
```

`env=bot_env` ortamı **değiştirmiyor, tamamen değiştiriyor.** Alt sürece yalnızca
`FULLET_PUSH_SUMMARY` geçiyor; `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
`FULLET_ALLOW_DB_WRITE`, hatta `PATH` yok. Script satır 29'da
`FULLET_ALLOW_DB_WRITE != "1"` görüp `return 1` ile çıkıyor — ve dönüş kodu
**kontrol bile edilmiyor.**

Aynı dosyadaki `_run_subprocess_once` bunu doğru yapıyor (satır 91-93:
`env = os.environ.copy(); env.update(...)`). Sadece bu çağrı atlanmış.

---

#### S1-6 — Bölgesel eşleştirme, normalize edilmemiş kolonla sorguluyor
**Dosya:** `scraper/matching.py:52-63`

```python
supabase.table("istasyonlar").select(...).eq("marka", brand).eq("il", city)
```

`city`, `normalize_city()` çıktısı (`"ISTANBUL"`, ASCII, büyük harf). DB'deki `il`
değeri istasyon envanteri botlarından geldiği için genelde aynı formatta — ama
`_load_brand_stations` (satır 267-270) aynı işi **Python tarafında normalize ederek**
yapıyor. İki farklı eşleştirme stratejisi aynı veriye uygulanıyor:

- `save_to_supabase` → `_station_targets` → **ham SQL eşitliği**
- `save_regional_prices_to_supabase` → `_load_brand_stations` → **normalize edilmiş eşleşme**

Opet/PO/BP/Aytemiz birinci yolu, TP/Total/Shell ikinciyi kullanıyor. Tek bir
eşleştirme yolu olmalı — ve DB'deki tek bir kayıtta bile Türkçe karakter varsa
birinci yol sessizce 0 hedef döndürür (fiyat hiçbir yere yazılmaz, hata da vermez).

Ayrıca `_regional_targets_from_loaded:289` ilçe eşleşmesini `district in
clean_text(...)` **alt dize** kontrolüyle yapıyor — `"MERKEZ"` gibi bir değer çok
sayıda yanlış ilçeyi eşleştirir.

---

#### S1-7 — `normalize_fuel` Türkçe "ş" harfini tanımıyor
**Dosya:** `scraper/normalization.py:63-81`

```python
text = clean_text(value).lower()      # "kurşunsuz 95" (ş korunuyor)
if "kursunsuz" in text or "benzin" in text or "95" in text:   # ← "kurşunsuz" eşleşmez
```

`clean_text` NFKC normalize ediyor ama harf çevirisi yapmıyor. `"kurşunsuz"` metni
yalnızca sondaki `"95" in text` fallback'i sayesinde doğru sınıflanıyor. Kaynak "95"
yazmayı bırakırsa (örn. "Kurşunsuz Benzin V/Max") sınıflama sessizce bozulur.
`CITY_REPLACEMENTS` burada da uygulanmalı.

---

### S2 — UYGULAMADA YANLIŞ GÖSTERİM

---

#### S2-1 — Yakıt filtresi tamamen ölü (❗ en görünür kullanıcı hatası)
**Dosya:** `fullet_flutter/lib/screens/modern_map_screen.dart:390-396`

```dart
List<Station> _stationsWithFuel(String fuelType) {
  return _stations
      .where((station) =>
          station.hasDisplayablePriceFor(fuelType) || station.isVisibleInApp)
      .toList(growable: false);
}
```

`_stations` listesi `SupabaseService._parseStations` içinde (satır 424) **zaten**
`isVisibleInApp == true` süzgecinden geçmiş. Yani `|| station.isVisibleInApp` her
zaman `true` → **koşulun tamamı her istasyon için doğru** → yakıt filtresi hiç
çalışmıyor.

Kullanıcı LPG'ye basınca LPG satmayan istasyonlar da haritada kalıyor ve
`formatMarkerPrice` onlara **"Yok"** yazıyor. `||` yerine `&&` olmalı (ya da yalnızca
`hasDisplayablePriceFor`).

Bu hata üç ayrı yerden yayılıyor:
- `_filteredStations` → harita marker'ları ve boş-durum kartı (satır 1714)
- `_drivingTargetStation` (satır 432) → sürüş banner'ında "`— TL`" gösteriyor (satır 1188)
- `_buildEmptyState` neredeyse hiç tetiklenmiyor — kullanıcı "fiyat yok" mesajı yerine
  "Yok" dolu bir harita görüyor

---

#### S2-2 — Marker fiyatı bayat, "en ucuz" tacı taze: harita kendiyle çelişiyor
**Dosya:** `modern_map_screen.dart:689-706`

```dart
final priceNum       = station.priceValueFor(selectedFuel);        // stale DAHİL
final trustedPriceNum = station.trustedPriceValueFor(selectedFuel); // yalnızca fresh
final isCheapest = trustedPriceNum != null && ... ;
```

Marker etiketi bayat fiyatı gösteriyor, ama "en ucuz"/"en mantıklı" rozeti yalnızca
taze fiyatlar arasından seçiliyor. Fiyatların %79'u bayat/bilinmiyor olduğu için
**kullanıcı ekranda 79,50 yazan bir marker görürken, mavi "en ucuz" rozeti 82,10 yazan
başka bir istasyonda duruyor.** Aynı çelişki `SmartStationService` (satır 48, 93),
`_StationCluster.minPriceFor` (satır 2137) ve `_stationsForZoom` (satır 783) için de geçerli.

Karar tek olmalı: ya bayat fiyat haritada hiç gösterilmez, ya da akıllı hesap da bayatı
(açık bir güven düşüşü etiketiyle) hesaba katar. Şu anki karışım en kötü seçenek.

---

#### S2-3 — "Güncel" etiketi yalan söyleyebiliyor
**Dosya:** `fullet_flutter/lib/models/station.dart:151-159, 178-197`

```dart
DateTime? get latestPriceUpdatedAt {
  final candidates = [
    ...prices.map((price) => price.updatedAt).whereType<DateTime>(),
    if (dataUpdatedAt != null) dataUpdatedAt!,     // ← istasyon satırının zamanı
  ];
  ...
}
```

`dataUpdatedAt` = `istasyonlar.guncellenme_tarihi`. Bu kolon `matching._station_targets`
tarafından **her bot koşusunda**, fiyat yazılmasa bile güncelleniyor (satır 74-79, 148-158).
Sonuç: fiyat üç haftalık olsa bile `getLastPriceChangeText()` "Güncel" ya da "2s önce"
diyebiliyor.

İlgili: `getLastPriceChangeText()` (satır 178) `priceHistory`'yi **yakıt tipine bakmadan**
tarıyor — motorin değişimini LPG kartında "3s önce" olarak gösterebilir.

---

#### S2-4 — Arama, Türkçe "İ" harfinde kırılıyor
**Dosya:** `modern_map_screen.dart:2535-2544`

```dart
String _normalize(String value) {
  return value.toLowerCase()
      .replaceAll('ı', 'i').replaceAll('ğ', 'g') ... ;   // 'İ' listede yok
}
```

Dart'ta `'İ'.toLowerCase()` → `'i' + U+0307` (birleşen nokta). `İSMAİL PETROL` →
`"i̇smai̇l petrol"`; kullanıcının yazdığı `"ismail"` bu dizede **bulunmaz.**
`brand_utils._normalizeBrandText` bu harfi ele alıyor, `_normalize` almıyor.

> **DÜZELTME (Faz 2, canlı doğrulama) — BU BULGU YANLIŞTI.**
> Dart 3.12.2'de `'İ'.toLowerCase()` **tek karakter** `'i'` (U+0069) döndürüyor;
> birleşen nokta üretilmiyor. Ölçüldü: `'İ'.codeUnits == [304]`,
> `'İ'.toLowerCase().codeUnits == [105]`. Eski `_normalize` `İSMAİL PETROL`'ü
> zaten `"ismail petrol"` yapıyordu ve `"ismail"` araması **çalışıyordu.**
> Canlı veride de sorun yok: `istasyonlar`ın 3.433 satırının **0**'ı birleşen
> nokta içeriyor, hepsi NFC; 933 isimde `İ` var ve hepsi doğru eşleşiyor.
>
> Yine de yapılan değişiklik korundu, ama **hata düzeltmesi olarak değil**:
> iki ayrı normalleştirici (`_normalize` + `_normalizeBrandText`) tek
> `utils/text_normalize.dart`'a indirildi. `_normalizeBrandText` içindeki
> `replaceAll('İ','i')` satırı `toLowerCase()`'ten sonra geldiği için zaten
> **ölü koddu** — silindi. U+0307 temizliği savunma amaçlı duruyor ve
> `text_normalize_test.dart` Dart tam Unicode eşlemesine geçerse düşecek
> şekilde davranışı kilitliyor.
>
> Bu, S1-2'den sonra denetimin **ikinci** yanlış bulgusu. Ders aynı:
> mekanizma iddiası ölçülmeden düzeltme yazılmamalı.

---

#### S2-5 — `fuelMatches` fazla gevşek
**Dosya:** `fullet_flutter/lib/utils/price_formatter.dart:48-72`

`source.contains(target) || target.contains(source)` ve `elektrik` için
`source.contains('ev')` — bugün 3 kanonik yakıt adıyla zararsız, ama `Elektrik`
devreye girdiğinde (EV pivotu senaryosu) yanlış eşleşme üretecek. Ayrıca
`Station.priceFor` **ilk eşleşmeyi** döndürüyor; bir istasyonda hem `Motorin` hem
`Motorin Ultra` satırı olsa hangisinin gösterileceği rastlantısal.

---

#### S2-6 — Fiyat alarmı zaman damgası yerel saatle yazılıyor
**Dosya:** `fullet_flutter/lib/services/price_alert_service.dart:84-85`

```dart
await ...update({'son_tetiklenme': now.toIso8601String()}).eq('id', alert.id);
```

`DateTime.now()` yerel saat, `toIso8601String()` offset yazmıyor. Postgres bunu UTC
olarak yorumluyor → Türkiye'de **3 saatlik kayma**. 24 saatlik tekrar-bildirim
koruması (satır 67-70) bu yüzden 21 saatte açılıyor. `toUtc()` gerekli.

---

### S3 — SESSİZ / ÖLÜ MEKANİZMALAR

---

#### S3-1 — `ops_report` Shell alarmlarını körü körüne kapatıyor
**Dosya:** `scraper/ops_report.py:216-217`

```python
resolve_system_alerts(source="bot:shell_bot.py")
resolve_system_alerts(source="bot:shell_station_bot.py")
```

Rapor temizse — ki eşikler istasyon *sayısına* bakıyor, fiyat *tazeliğine* değil —
Shell botunun gerçekten patlamış olup olmadığına bakılmaksızın alarmları kapatıyor.
"Tolere edilen bot" döneminden kalma; son commit tolere listesini boşalttı ama
bu iki satır kaldı. **Shell'in kalıcı arızası hâlâ görünmez.**

---

#### S3-2 — Ardışık hata sayacı mevcut koşuyu iki kez sayıyor
**Dosya:** `scraper/telemetry.py:42-53, 83-90`

`record_bot_run` önce satırı **insert ediyor** (satır 42), sonra
`_check_consecutive_failures` çağrılıyor (satır 62). Orada:

```python
# Mevcut çalışmayı (henüz insert edilmedi) dahil et      ← yorum yanlış
statuses = [current_status] + [r.get("status") for r in recent]
```

`recent` sorgusu az önce yazılan satırı zaten içeriyor. Tek bir hata
`consecutive_failures = 2` üretiyor → `critical` alarm ilk hatada patlıyor.
Alarm yorgunluğu; gerçek ardışık hatalar sıradanlaşıyor.

---

#### S3-3 — `low_priority` düşürme işi hiçbir şey yapmıyor
**Dosyalar:** `database/auto_price_staleness.sql:59-76`, `models/station.dart:89-90`

pg_cron JOB 3, 7 gündür güncellenmemiş istasyonları `visible → low_priority`'ye
düşürüyor. Ama uygulamada:

```dart
bool get isVisibleInApp =>
    visibilityStatus == 'visible' || visibilityStatus == 'low_priority';
```

`low_priority` da gösteriliyor, RPC de (`create_postgis_rpc.sql:34`) her ikisini
kabul ediyor. **Güvenlik mekanizması kurulmuş ama hiçbir yere bağlanmamış.**

---

#### S3-4 — Push token temizliği aktif kullanıcıların token'ını siliyor
**Dosya:** `database/auto_price_staleness.sql:79-89`

Yorum "90 günde hiç **kullanılmamış** token'ları sil" diyor, kod
`olusturulma_tarihi < NOW() - 90 days` yazıyor. `son_guncelleme` kolonu tam bu iş için
var (`rls_policies.sql:10`) ama kullanılmıyor. 90 günlük sadık kullanıcı push almayı
kesiyor.

---

#### S3-5 — Push altyapısı uçtan uca kopuk
**Dosyalar:** `supabase/functions/fiyat-push/index.ts:88-101`, `services/notification_service.dart`

- Edge function yalnızca **Expo** token'larına gönderiyor; FCM token'ları sayılıp
  `pendingFcm` olarak raporlanıyor, **gönderilmiyor** (satır 96-104).
- Flutter uygulaması `firebase_messaging` kullanmıyor ve `push_tokens` tablosuna
  **hiç yazmıyor** — depoda tek bir `push_tokens` insert'i yok.
- Yani `send_summary_push` her koşuda çağrılabilir ama hiçbir cihaza ulaşmaz.

Ölü kod değil, **ölü ürün yüzeyi** — ya tamamlanmalı ya da kaldırılmalı.

---

#### S3-6 — `get_nearby_stations` dört ayrı dosyada tanımlı
**Dosyalar:**
- `database/create_postgis_rpc.sql` (5 argüman)
- `supabase/migrations/20260505195000_production_hardening.sql:304` (4 argüman)
- `supabase/migrations/20260708120100_...:15` (4 argüman + GRANT 4 arg)
- `supabase/migrations/20260708130000_...:20` (5 argüman)

Migration'lar sırayla uygulanınca son durum doğru. Ama `database/*.sql` scriptleri
elle çalıştırılan **ikinci bir doğruluk kaynağı.** Biri `supabase db push` yaptıktan
sonra `database/create_postgis_rpc.sql`'i (veya tersini) çalıştırırsa iki overload
birlikte kalabilir → PostgREST çağrıyı çözemez → uygulama sessizce
`_fetchStationsByBrandsWholeCountry` fallback'ine düşer (2.617 istasyonu telefonda
sayfalayarak tarar).

`supabase_service.dart`'taki üç katmanlı savunmacı fallback zinciri (satır 87-95,
216-229, 283-292) bu belirsizliğin ürünü.

---

#### S3-7 — Testler var, CI'da hiç koşmuyor
**Dosyalar:** `.github/workflows/otopilot.yml`, `.github/workflows/admin-panel-pages.yml`

13 Flutter testi (`test/*.dart`) ve 20 Python testi (`scraper/test_*.py`) mevcut —
`test_shell_bot.py` bile Shell'in motorin kolonunu doğruluyor. **Hiçbir workflow
`pytest` ya da `flutter test` çalıştırmıyor.** `scripts/release_check.ps1` yerel,
elle çalıştırılan bir script.

`test_zero_cost_unchanged_prices_skipped` gibi testler doğru davranışı kilitliyor
ama kimse çalıştırmıyor.

---

#### S3-8 — `main.dart` başlangıçta çökebilir
**Dosya:** `fullet_flutter/lib/main.dart:40`

```dart
await dotenv.load(fileName: '.env');    // try/catch yok
```

`.env` asset'i eksikse `dotenv.load` **fırlatır** ve `runApp` hiç çağrılmaz →
kullanıcı beyaz ekran görür. Hemen altındaki `_ConfigurationErrorApp` (satır 44-50)
yalnızca "yüklendi ama boş" durumunu yakalıyor — asıl riskli durumu değil.
`.env` `pubspec.yaml:40`'ta asset olarak listelenmiş ama `.gitignore`'da; herhangi bir
temiz checkout + build bu tuzağa düşebilir.

---

#### S3-9 — Sürüm numarası üç yerde elle yazılmış
**Dosyalar:** `services/app_heartbeat_service.dart:11`, `modern_map_screen.dart:1355`,
`modern_map_screen.dart:1752` → hepsi `'1.0.2'`; `pubspec.yaml:4` → `1.0.2+5`.

Kohort analizini `app_heartbeats.app_version` üzerinden yapıyorsunuz. Sürüm
yükseltilip bu üç sabit unutulursa **retention verisi sessizce yanlış kohorta yazılır.**
`package_info_plus` ile tek kaynaktan okunmalı.

---

#### S3-10 — Hata yutma politikası tutarsız
**Dosya:** `services/supabase_service.dart`

`upsertUserProfile:444` → `catch (_) {}` (tamamen sessiz),
`addFavorite:478` / `removeFavorite:488` → sessiz,
`getUserFavorites:464` → sessizce `{}` döndürüyor,
ama `deleteUserData:451` bilinçli olarak yutmuyor (yorumu da var).

Favori ekleme sunucuda başarısız olursa kullanıcı yerelde favorilenmiş görüyor,
başka cihazda göremiyor — ve hiçbir yerde iz kalmıyor.

---

#### S3-11 — Diğer küçük bulgular

| Dosya:satır | Bulgu |
|---|---|
| `matching.py:175` | `inserted.data[0]["id"]` — insert boş dönerse `IndexError`; yalnızca çağıranın `try` bloğunda `skipped++` olarak yutulur |
| `database_writes.py:97-99` | `veri_kaynagi` fallback'i istisna **metnine** bakıyor (`if "veri_kaynagi" not in str(exc)`) — kırılgan |
| `db_utils.py:233-251` | `CANONICAL_FUELS` içindeki `"Elektrik"` her koşuda "unknown" yazma denemesi üretiyor (gereksiz yazma trafiği) |
| `backend_health_check.py:231` | Geçerli yakıt listesi `("Kursunsuz 95","Motorin","LPG")` — `Elektrik` eklenirse sağlık kontrolü kırmızıya döner |
| `shell_bot.py:95` | `int(os.environ.get("SHELL_MAX_TARGETS_PER_RUN", 150))` — geçersiz değer `ValueError` ile botu düşürür |
| `modern_map_screen.dart:1570` | `onCameraIdle` her seferinde `_scheduleMarkerRefresh(force: true)` → tüm marker ikonları yeniden çiziliyor |
| `station.dart:193-196` | `_relativeTime`, sunucu saati ileriyse negatif farkı "Güncel" sayıyor |

---

## 2. YOL HARİTASI

Sıralamanın tek bir mantığı var: **önce ölçüm aletini onar, sonra veriyi, en son
görüntüyü.** Kirli aletle yapılan her düzeltme doğrulanamaz.

---

### FAZ 0 — GÖRÜŞ AÇ (yarım gün) — *diğer her şeyin önkoşulu*

Şu an hiçbir düzeltmenin işe yarayıp yaramadığını göremezsiniz. Önce bunu çözün.

1. **`FULLET_FAIL_ON_BOT_ERROR: "0"` satırını kaldır** (`otopilot.yml:159`).
   → Retry + alarm altyapısı canlanır. *(S0-2)*
2. **Botlara dürüst çıkış kodu ver.** Her bot dosyasının `__main__` bloğuna:
   scrape 0 kayıt döndürdüyse veya istisna yakalandıysa `raise SystemExit(1)`.
   `news_bot.py:131` kalıbını kopyalayın. *(S0-1)*
3. **`bot_runs`'a `records_written` kolonu ekle.** `SaveSummary` zaten
   `stations_touched`/`prices_touched` taşıyor — bot bunu stdout'a basıp
   `run_all_bots` telemetriye yazsın. 0 ise `status='empty'` + alarm.
4. **`ops_report.py:216-217`'deki iki `resolve_system_alerts` satırını sil.** *(S3-1)*
5. **`telemetry._check_consecutive_failures` çift saymasını düzelt** — ya insert'ten
   önce çağır, ya `recent`'ten mevcut koşuyu çıkar. *(S3-2)*
6. **CI'ya test adımı ekle:** `pytest scraper/` + `flutter test`. Mevcut 33 test zaten
   yazılmış durumda. *(S3-7)*

**Doğrulama:** Bir botun URL'sini kasten bozun. Beklenen: workflow kırmızı,
`system_alerts`'ta kayıt, `bot_runs.status != 'success'`.

---

### FAZ 1 — VERİ HATTINI DÜZELT (2–3 gün)

Faz 0 olmadan bu fazın hiçbir adımı doğrulanamaz.

7. **`quarantine_old_prices.py` env hatasını düzelt** — `env=bot_env` yerine
   `os.environ.copy()` + update; dönüş kodunu kontrol et. *(S1-5)*
   → Tek satırlık düzeltme, muhtemelen aylardır çalışmayan bir bakım işini geri getirir.
8. **`son_dogrulama` (last_verified_at) kolonunu ekle.** *(S0-3 — en yüksek değerli düzeltme)*
   - `fiyatlar`'a yeni `TIMESTAMPTZ` kolon.
   - Botlar fiyat değişmese de **her doğrulamada** bu kolonu bump etsin
     (`_bulk_upsert_prices` atlama optimizasyonu korunur — sadece bu kolon yazılır).
   - pg_cron JOB 1/2 `son_guncelleme` yerine `son_dogrulama`'ya baksın.
   - `son_guncelleme` yalnızca "son fiyat değişimi" anlamında kalsın (trigger zaten öyle davranıyor).
9. **Tazelik eşiklerini tek yerden yönet.** *(S0-4)* Kaynak: `fresh ≤ 12h`,
   `stale ≤ 48h`, sonrası `unknown`. Admin panelin 72'sini, `quarantine_old_prices`'ın
   72'sini, `ops_report`'un 48'ini bu tek tanıma bağlayın.
10. **Kolon eşlemesini başlık metnine bağla.** *(S1-1, S1-2, S1-3)*
    Ortak bir `resolve_columns(header_row) -> {fuel: index}` yardımcısı yazın;
    `normalization.normalize_fuel` zaten "lpg"/"otogaz"/"motorin" metnini tanıyor.
    Uygulama sırası: `shell_bot` → `po_bot` → `bp_bot` → `aytemiz_bot` → `tp_bot`.
    Sabit indeks kalan hiçbir bot bırakmayın.
11. **Çapraz doğrulama kapısı ekle.** *(S1-4)* Yazmadan önce: bir markanın bir yakıttaki
    medyanı, diğer markaların medyanından **%10'dan fazla** saparsa → yazma, `system_alerts`'a
    `critical` düş. Bu kural tek başına Shell LPG'yi ilk gün yakalardı.
12. **Eşleştirmeyi tekilleştir.** *(S1-6)* `_station_targets`'ın ham SQL eşitliğini
    `_load_brand_stations`'ın normalize eden yoluna taşıyın; ilçe eşleşmesini alt dize
    yerine tam eşleşmeye çevirin.
13. **`normalize_fuel`'e `CITY_REPLACEMENTS` uygula.** *(S1-7)* Üç satır.

**Doğrulama (kapı):** Faz 1 sonunda `ops_report.py` 7 markanın **hepsinde** taze fiyat
görmeli ve marka-yakıt medyanları %10 bandı içinde olmalı. Olmuyorsa Faz 2'ye geçmeyin.

---

### FAZ 2 — UYGULAMADAKİ YALANI KES (1–2 gün)

Veri düzeldikten sonra görüntüyü düzeltin — tersi sırada neyin düzeldiğini ayırt edemezsiniz.

14. ✅ **`_stationsWithFuel`'deki `||`'ı `&&` yap.** *(S2-1)* Tek karakter, en görünür
    kullanıcı hatasını kapatır. Sonrasında boş-durum kartı gerçekten çalışmaya başlar.
15. ✅ **Bayat fiyat politikasını netleştir ve tek yerde uygula.** *(S2-2)*
    Önerim: bayat fiyat haritada gösterilsin **ama** marker'da görsel olarak ayrışsın
    (zaten `marker_icon_factory.dart:86` turuncu paleti var) **ve** "en ucuz"/"en mantıklı"
    hesabı da aynı havuzu kullansın. Şu anki iki farklı havuz kabul edilemez.
    → Uygulandı: `Station.priceValueFor` tek havuz (fresh+stale, unknown hariç);
    `SmartStationService` (2 yer), marker tacı, `_stationsForZoom`, `minPriceFor`
    hepsi buna bağlandı. Eşit fiyatta taze olan tacı alır. `trustedPriceValueFor`
    yalnızca **fiyat alarmında** kaldı (bildirim göndermenin eşiği gösterimden yüksek).
16. ✅ **`latestPriceUpdatedAt`'ten `dataUpdatedAt`'i çıkar.** *(S2-3)* İstasyon satırının
    güncellenme zamanı fiyat tazeliği değildir. `getLastPriceChangeText`'i yakıt tipine
    duyarlı hale getirin.
    → Ayrıca `station_bottom_sheet.dart`'taki `?? station.dataUpdatedAt` geri düşüşü
    kaldırıldı; asıl "Güncel" yalanı **orada** görünüyordu (`getLastPriceChangeText`'in
    hiç çağrılmadığı ortaya çıktı).
17. ⚠️ **`_normalize`'a `'İ'` çevirisini ekle** (`toLowerCase` öncesi). *(S2-4)*
    → **Bulgu yanlıştı** (bkz. S2-4 düzeltme notu). Hata yoktu; değişiklik
    normalleştirici birleştirmesi olarak korundu.
18. ✅ **`son_tetiklenme`'yi `toUtc()` ile yaz.** *(S2-6)*
19. ✅ **`dotenv.load`'ı try/catch'e al**, hata durumunda `_ConfigurationErrorApp`. *(S3-8)*
    → Yalnızca `load`'ı sarmalamak YETMİYOR: `dotenv.env` getter'ı da
    `NotInitializedError` fırlatıyor (flutter_dotenv 6.0.1, `dotenv.dart:39`),
    yani çökme bir satır aşağı kayardı. `dotenv.isInitialized` kontrolü eklendi.
20. ✅ **Sürüm numarasını `package_info_plus`'tan oku**, üç sabiti sil. *(S3-9)*
    → `utils/app_version.dart` tek kaynak; `main()` içinde `AppVersion.init()`
    heartbeat'ten ÖNCE çağrılıyor. Yan etki: `package_info_plus` `win32`'yi
    `<6.0.0` serbest bıraktığı için çözümleyici 5.2.0'ı seçti; o sürüm Dart
    3.4'te kaldırılan `UnmodifiableUint8ListView`'i kullanıyor ve `flutter test`
    derlemesini kırıyordu. `win32: ^5.5.4` sabitlendi, `sdk` alt sınırı
    gerçeği yansıtacak şekilde `>=3.3.0` yapıldı.

---

### FAZ 0–2 DENETİMİ (3 Ağustos 2026) — kapatılan boşluklar

Faz 0/1/2 tamamlandıktan sonra yapılan gözden geçirme, üretim verisiyle
doğrulanan **dört yeni bulgu** çıkardı. Hepsi düzeltildi.

#### D1 — Hedef kapsaması ölçülmüyordu (Faz 0'ın kapatmadığı boşluk) ❗
Faz 0 yalnızca *"bot HİÇ kayıt üretmedi mi?"* sorusunu görünür kıldı
(`empty`). *"Bot hedeflerinin çoğunu kaybetti mi?"* sorusu sorulmuyordu.

Canlı `bot_runs.stdout_excerpt` üzerinden 8 koşu sayıldı — sonuç her koşuda
neredeyse aynı:

| Koşu | Denenen hedef | `Element is not visible` | Grid okundu |
|---|---|---|---|
| 02 Ağu 16:24 | 42 | 27 | 11 |
| 02 Ağu 11:01 | 45 | 27 | 13 |
| 02 Ağu 06:23 | 44 | 29 | 10 |
| 01 Ağu 22:18 | 40 | 34 | 5 |

**Shell hedeflerinin ~%63'ünü her koşuda sessizce kaybediyordu** ve yine
yüzlerce kayıt döndürdüğü için `success` görünüyordu. Sonuç canlıda:
Shell'in 1.152 fiyat satırının %26'sı taze, %36'sı **bayat**, %38'i
bilinmiyor — diğer altı markada bayat **sıfır**.

*Kök neden:* `page.locator(...).click(force=True)` + sabit
`wait_for_timeout(750)`. DevExpress combobox'ı grid callback'i sürerken
DOM'da kalıyor ama görünmez oluyor; `force` **görünürlük kontrolünü
atlamaz**, dolayısıyla Playwright fırlatıyor ve hedef `except` tarafından
yutuluyordu.

*Düzeltme:* sabit uyku yerine görünürlük bekleme (`_settle` + `wait_for`),
hedef başına bir kez retry, ve kapsama muhasebesi:
`[RECORDS] ... targets_ok=A targets_total=B` →
`run_all_bots` → yeni **`degraded`** bot_runs durumu + `warning` alarmı
(eşik: `db_utils.MIN_TARGET_COVERAGE` = %70).
`degraded` pipeline'ı kırmızıya döndürmez — kısmi veri doğrudur ve exit 1
9 dakikalık kazımayı boşuna tekrarlardı. Migration:
`database/add_bot_runs_degraded_status.sql` (canlıya uygulandı).

#### D2 — Çapraz doğrulama kapısı, koruduğu veriyi siliyordu ❗
`save_to_supabase` / `save_regional_prices_to_supabase` sonunda
"bu koşuda raporlanmayan yakıtları `unknown` yap" süpürgesi çalışıyor.
Kapı bir yakıtı reddedince o yakıt öğelerden düşüyor, süpürge de onu
"raporlanmadı" sayıp **mevcut sağlam fiyatları `unknown`'a çeviriyordu.**
Yani Faz 1'de eklenen güvenlik mekanizması, tek bir hatalı koşuda o markanın
o yakıttaki tüm geçmişini silebilirdi. `apply_sanity_gate` artık reddedilen
yakıt kümesini çağırana döndürüyor ve o yakıtlar süpürgeden muaf tutuluyor.

#### D3 — Faz 2'nin 18/19/20. maddeleri (yukarıda işaretlendi)

#### D4 — "İLÇE/İL" birleşik `il` değerleri
20 istasyonun `il` kolonu `MERAM/KONYA` biçimindeydi ve `_station_targets`
`.eq("il","KONYA")` sorguladığı için **20'sinin de taze fiyatı yoktu.**
`normalization.split_province_district` / `normalize_province` eklendi
(81 il listesine bakar, konuma değil) ve ingest + okuma yollarına bağlandı;
`database/repair_composite_province_values.sql` mevcut satırları onardı
(18/20 taşındı, distinct `il` 119 → 108). Kalan 2 satır `unique_isim_ilce`
kısıtına takılıyor ve **kopya değil** — koordinatları hedeflerinden 2,4 km
ve 3,5 km uzakta, yani ayrı gerçek istasyonlar. Asıl kusur kısıtta: `isim`
bu markalarda marka adı olduğu için aynı ilçedeki iki Petrol Ofisi şemada
temsil edilemiyor. Kısıtı değiştirmek istasyon kimliği/dedupe mantığını
etkilediğinden ayrı bir karar olarak bırakıldı.

#### Doğrulanıp REDDEDİLEN bulgu — madde 12 (S1-6, eşleştirmeyi tekilleştir)
Yol haritası "DB'de Türkçe karakter varsa `_station_targets` sessizce 0 hedef
döndürür" diyordu. Canlı ölçüm bunu **çürüttü**: Türkçe `ilce` içeren 234
istasyonun **%96,2'sinin** taze fiyatı var; ASCII olanlarda bu oran %52,6.
Sebep: bu yolu kullanan botlar (Opet/PO/BP/Aytemiz) **il düzeyinde** fiyat
yazıyor, `item["ilce"]` boş, dolayısıyla `ilike("ilce", ...)` filtresi hiç
çalışmıyor. Madde 12'nin gerekçesi mevcut bot bileşiminde geçerli değil;
eşleştirmeyi tekilleştirmek 1.100+ istasyonun çalışan yazma yolunu riske
atacağı için **yapılmadı**. Bu, denetimin **üçüncü** yanlış bulgusu
(S1-2 ve S2-4'ten sonra) — ders yine aynı: mekanizma iddiası ölçülmeden
düzeltme yazılmamalı.

---

### FAZ 0–2 DENETİMİ — KAPATILAN İKİ BULGU (3 Ağustos 2026, ikinci tur)

#### B1 — `degraded`, kritik "arka arkaya BAŞARISIZ" alarmına dönüşüyordu ❗
`telemetry.record_bot_run` `success/ok` olmayan **her** durumu hata sayıyor,
`_check_consecutive_failures` de geçmiş `degraded` satırlarını hata olarak
sayıp seriyi uzatıyordu. Üretimde fiilen patladı:

```
2026-08-02T23:11:19  warning   shell_bot.py hedeflerin çoğunu okuyamadı
2026-08-02T23:11:20  critical  shell_bot.py arka arkaya başarısız
```

23:00 ve 23:26'daki iki `degraded` koşu bu alarmı açtırdı — oysa bot her iki
koşuda da yüzlerce fiyat yazmıştı. `degraded` tasarım gereği "veri yazıldı ama
eksik" demek. `NON_FAILURE_STATUSES` eklendi; `degraded` artık seriyi kırar ve
eski hata alarmını kapatır (kapsama uyarısı farklı `title` ile açık kalır).
4 regresyon testi, biri gerçek hataların HÂLÂ eskale ettiğini korur.

#### B2 — Kapsama sayıları hiçbir yerde kalıcı değildi
`_compact_log` stdout'un **ilk** 4000 karakterini saklar; `[RECORDS] …
targets_ok=A targets_total=B` satırı ~150 hedeflik koşunun **sonunda** basılır.
Canlı kontrol: 20 `shell_bot` kaydının **hiçbirinde** kapsama satırı yok.
Kapsama yalnızca `system_alerts.metadata`'da ve yalnızca `degraded` koşular
için kalıyordu — başarılı koşuda %71 mi %100 mü olduğu, yani eşiğe doğru
**trend**, görülemiyordu. (İroni: D1 teşhisi tam da `stdout_excerpt` okunarak
yapılmıştı; düzeltmeden sonra o yöntem çalışmıyor.)
`bot_runs.targets_ok` / `targets_total` kolonları eklendi
(`database/add_bot_runs_target_coverage.sql`); kapsama artık `status`'ten
bağımsız olarak **her** koşuda yazılıyor.

---

### FAZ 3 (YENİDEN TANIMLANDI) — İSTASYON VERİSİ: TABAN ÖLÇÜMÜ

Kullanıcı Faz 3'ü "tüm Türkiye'deki istasyonların konumları, eksik ilçeler ve
kopya kayıtlar" olarak yeniden tanımladı. Aşağıdaki 21–25. maddeler
(ölü mekanizmalar) **ertelendi**.

**Taban ölçümü, canlı veri, 3 Ağustos 2026 — salt-okunur.**

Toplam **3.433** istasyon. (Hedef olarak anılan 12.000+ ile arada büyük fark
var; Türkiye'de ~13.000 istasyon olduğu düşünülürse kapsama ~%26. Bu bir
*temizlik* değil *toplama* işi — ayrı karar.)

**Kritik metodoloji notu:** ham sayılar felaket görünüyor ama neredeyse
tamamı **pasif** satırlardan geliyor. Uygulama yalnızca `aktif` istasyonları
gösterir:

| kusur | ham sayı | AKTİF içinde |
|---|---|---|
| `il` 81 il listesinde değil | 292 | **0** |
| koordinat yok | 182 | **0** |
| `veri_kaynagi` boş | 353 | **0** |
| `ilce` boş | 591 | 29 (%1,1 — ve %100 taze) |
| fiyat satırı yok | 584 | 142 |

**Aktif 2.636 istasyonun %98,9'u kusursuz.** 797 pasif satır 1.065 `unknown`
fiyat satırı taşıyor ve **sıfır** tazesi var — eski moloz, doğru şekilde
gizli. `aktif` bayrağı görevini yapıyor.

`normalize_province` bir **doğrulayıcı değil**, normalleştiricidir: tanımadığı
değeri aynen geri verir (`'BILINMIYOR' -> 'BILINMIYOR'`). Geçerlilik ölçümü
`PROVINCES` kümesine karşı yapılmalı.

#### Aktiflerde kalan gerçek kusurlar (Faz 3'ün asıl kapsamı)

**F3-1 — 100 aktif kopya çifti (<150m, aynı marka).**
98'inde **ikisinde de** fiyat var (bölünmüş veri); **6'sı aynı yakıtta farklı
fiyat gösteriyor** — kullanıcı aynı istasyonu haritada iki pinde iki fiyatla
görüyor (ör. DİYARBAKIR ÇEVRE YOLU: LPG 33,94 `fresh` / 38,51 `unknown`).
51 çift "jenerik marka adı" vs "gerçek isim". Kaynak dağılımı suçluyu
gösteriyor: **66x Shell'in fiyat botu kendisiyle**, 29x TotalEnergies API'si
kendisiyle. Yani sorun iki bot arasında değil, **dedupe anahtarında**:
`unique_isim_ilce` kısıtında `isim` bu markalarda marka adı olduğu için aynı
ilçedeki iki istasyon temsil edilemiyor — D4'te "ayrı karar" diye bırakılan
kısıt sorunu tam olarak budur.

**F3-2 — 142 aktif istasyonun hiç fiyat satırı yok.**
TotalEnergies 134, Türkiye Petrolleri 8. Hepsi *istasyon* botlarından geliyor
(`exapi/stations`, `tppd.com.tr/tr/stationmaplist`); fiyat botları bunları hiç
eşleştirmiyor. Uygulamada görünür ama kalıcı olarak fiyatsız.

**F3-3 — Shell tazeliği (kapasite).** 94 öncelikli + koşu başına 56 slot →
tam tur **8 koşu = 48 saat**, `fresh` penceresi 12 saat. Öncelikli olmayan bir
ilçe tasarım gereği zamanın ~%25'inde taze olabilir. Canlı doğrulama birebir:
öncelikli %62,6 taze / diğer **%20,3** taze, %57,7 bilinmiyor. Shell tüm
istasyonların %41'i. Son 24 saatteki 7 Shell koşusunun **3'ü `degraded`**.

---

### FAZ 3 (ESKİ) — ÖLÜ MEKANİZMALARI KAPAT (yarım gün) — *ertelendi*

Bunlar bugün zarar vermiyor ama gelecekte yanlış güven üretir.

21. **`low_priority` kararını ver:** ya uygulamada gerçekten düşür (`isVisibleInApp`'ten
    çıkar veya marker'da soluklaştır), ya pg_cron JOB 3'ü kaldır. *(S3-3)*
22. **Push token temizliğini `son_guncelleme`'ye çevir.** *(S3-4)*
23. **Push altyapısına karar ver:** *(S3-5)* Kullanıcı sayısı 1 iken FCM entegrasyonu
    tamamlamak yanlış yatırım — **kaldırmayı öneriyorum.** `fiyat-push` fonksiyonu,
    `send_summary_push` çağrıları ve `push_tokens` tablosu ölü yüzey olarak kalırsa
    bir sonraki denetimde yine "çalışıyor mu?" diye zaman harcarsınız.
24. **SQL doğruluk kaynağını teke indir.** *(S3-6)* `database/*.sql` içindeki
    fonksiyon tanımlarını `supabase/migrations/`'a taşıyın; `database/` yalnızca
    tek seferlik onarım scriptleri için kalsın ve README'de bu net yazsın.
    `20260708120100` dosyası `20260708130000` tarafından tamamen eziliyor — süperseded
    olduğu dosya başına yazılmalı.
25. **`upsertUserProfile` / `addFavorite` / `removeFavorite`'ın sessiz `catch`'lerine
    en azından `debugPrint` + Crashlytics kaydı ekle.** *(S3-10)*

---

### FAZ 4 — REGRESYON KİLİDİ (yarım gün)

Bulunan her hata sınıfı için bir test. Bunlar olmadan aynı hatalar geri gelir.

- `shell_bot` / `po_bot` / `bp_bot` / `aytemiz_bot` için **başlık tabanlı kolon
  çözümleme testi** (kayıtlı HTML fixture ile).
- **Çapraz doğrulama kapısı testi:** %20 sapan bir marka medyanı yazmayı engelliyor mu?
- **Boş scrape testi:** bot 0 kayıt döndürdüğünde `SystemExit(1)` atıyor mu?
- **`_stationsWithFuel` testi:** LPG seçiliyken LPG'siz istasyon listede yok.
- **Tazelik testi:** `son_dogrulama` bump edilen bir fiyat 12 saat sonra hâlâ `fresh` mi?
- Hepsi CI'da (Faz 0, madde 6).

---

## 3. SIRALAMANIN GEREKÇESİ

**Neden Faz 0 önce?** Şu anda bir düzeltme yaptığınızda işe yarayıp yaramadığını
göremiyorsunuz — bot patlasa da yeşil, veri ölü olsa da yeşil. Aleti onarmadan
ölçüm yapılmaz. Faz 0 yarım gün ve geri kalan her şeyin doğrulanabilirliğini sağlar.

**Neden Shell LPG ilk sırada değil?** Çünkü tek başına düzeltilirse **aynı sınıftan
başka hataların olup olmadığını bilemezsiniz.** S1-2 (PO/BP kolon çelişkisi) tam da
bunu gösteriyor: Shell'e odaklanırken aynı hata iki bot daha yapıyor olabilir.
Faz 1'in 10. maddesi (başlık tabanlı eşleme) tüm sınıfı birden kapatır ve 11. madde
(çapraz doğrulama) bir daha olmasını engeller.

**Neden `son_dogrulama` bu kadar yukarıda?** Çünkü diğer tüm parser'ları düzeltseniz
bile bu kolon olmadan fiyatların önemli bir kısmı **doğruyken bayat görünmeye devam
edecek.** "Taze veri çekemiyor" şikâyetinin bir kısmı parser hatası değil, muhasebe hatası.

**Neden uygulama en sonda?** `&&` düzeltmesi (S2-1) tek karakterlik ve çok çekici —
ama önce yaparsanız, kullanıcı bu sefer "yakıt filtresi çalışıyor ama hepsi bayat"
görür. Veri hattı düzelmeden görüntü düzeltmek şikâyeti dönüştürür, çözmez.

---

## 4. KARAR PROTOKOLÜ İLE İLİŞKİ

`FULLET_KARAR_PROTOKOLU.md` Adım 1'de üç madde vardı; bu denetim onları genişletiyor:

| Karar protokolü maddesi | Bu yol haritasındaki karşılığı | Durum |
|---|---|---|
| Shell LPG kolonunu düzelt | Faz 1 / madde 10 | Genişletildi: 5 botun tamamı |
| Çapraz doğrulama kapısı ekle | Faz 1 / madde 11 | Aynen |
| Sessiz başarısızlığı bitir | Faz 0 / madde 1-3 | Genişletildi: CI bayrağı da dahil |
| Opet/PO/TP/Aytemiz neden yazmıyor? | S1-2, S1-5, S1-6 | **Cevaplandı** (aşağıda) |

**"4 bot neden hiç taze fiyat yazmıyor?" — CEVAP (2 Ağustos, canlı veriyle kesinleşti):**

Hipotezlerimden ikisi yanlıştı, biri doğruydu:

| Hipotez | Sonuç |
|---|---|
| Parser kırık, bot sessizce boş dönüyor (S0-1) | ❌ **Yanlış** — botlar çalışıyor ve yazıyordu |
| PO kolon indeksleri yanlış (S1-2) | ❌ **Yanlış** — indeksler doğruydu (yukarıdaki düzeltme) |
| Tazelik muhasebesi bozuk (S0-3) | ✅ **DOĞRU — tek ve yeterli sebep** |

Canlı `bot_runs` + `fiyatlar` zaman damgaları mekanizmayı birebir gösterdi:

```
01 Ağu 22:13  Opet/PO/Aytemiz/TP yazdı        -> fresh
02 Ağu 06:14  bot koştu, fiyat aynı, yaş 8s   -> diff ATLADI (doğrulama izi yok)
02 Ağu 10:14  pg_cron (12s eşiği)             -> stale      <- "0 taze fiyat"
02 Ağu 16:20  bir sonraki koşu                -> tekrar fresh
```

Yani dört marka **ölü değildi, salınıyordu.** Karar protokolündeki "%0 taze"
ölçümü, salınımın bayat evresinde alınmış bir anlık görüntüydü. BP ve
TotalEnergies'in aynı anda taze görünmesinin sebebi de fiyatlarının o koşuda
gerçekten değişmiş olmasıydı (değişen fiyat diff'i atlamaz).

**Faz 1 sonrası ölçüm (aynı gün, düzeltmelerden sonra):**

| Marka | Önce (taze) | Sonra (taze) | Bayat |
|---|---|---|---|
| TotalEnergies | %50,0 | **%89,6** | 0 |
| Opet | **%0,0** | **%87,7** | 0 |
| Petrol Ofisi | **%0,0** | **%47,2** | 0 |
| Aytemiz | **%0,0** | **%45,8** | 0 |
| Türkiye Petrolleri | **%0,0** | **%45,1** | 0 |
| BP | %19,0 | **%42,2** | 0 |

Altı markada da **bayat sayısı sıfır** — salınım tamamen durdu. Kalan `unknown`
satırlar meşru: o istasyonda satılmayan yakıtlar (LPG) ve hiç doldurulmamış
`Elektrik`. Doğrulama: `Kursunsuz 95` ve `Motorin` taze sayıları (1394), altı
botun yazdığı istasyon toplamıyla birebir eşleşiyor.

> Not: Karar protokolü "yeni özellik yok, yalnızca doğruluk borcu" diyordu. Bu yol
> haritasının tamamı o tanıma uyuyor — hiçbir maddede yeni kullanıcı özelliği yok.
> Faz 3'ün 23. maddesi (push'u kaldır) **yüzey azaltıyor**, artırmıyor.

---

## 5. TAHMİNİ SÜRE

| Faz | Süre | Kritiklik |
|---|---|---|
| Faz 0 — Görüş aç | 0,5 gün | Zorunlu önkoşul |
| Faz 1 — Veri hattı | 2–3 gün | Şikâyetin ana kaynağı |
| Faz 2 — Uygulama | 1–2 gün | Görünür kullanıcı hatası |
| Faz 3 — Ölü mekanizmalar | 0,5 gün | Gelecekteki yanlış güveni önler |
| Faz 4 — Regresyon kilidi | 0,5 gün | Kalıcılık |
| **Toplam** | **5–7 gün** | |
