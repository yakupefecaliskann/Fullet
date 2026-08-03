# FULLET — BÜYÜK KAPANIŞ VE TEMİZLİK OPERASYONU
## Uygulama Planı

**Tarih:** 3 Ağustos 2026
**Kapsam:** Faz 0–3 kanıtlı kapanış + kod temizliği + moloz veri + ertelenen 21–25. maddeler
**Durum:** ✅ **ONAYLANDI — 3 Ağustos 2026.** Uygulama başladı.

## ONAYLANAN KARARLAR (kullanıcı, 3 Ağustos 2026)

| # | Karar | Sonuç |
|---|---|---|
| 1 | **Push altyapısı (madde 23): KALDIR.** "Kullanılmayan bir ölü kodu sistemde tutmak istemiyorum." | `fiyat-push` Edge Function, `push_tokens` tablosu, `send_summary_push`, `summary_push.py` kaldırılır. Madde 22 böylece düşer. **Yerel bildirimler (`NotificationService`) KALIR** — onlar çalışıyor. |
| 2 | **Shell'in 178 fiyatsız istasyonu (A2): SEÇENEK (b) — GİZLE.** "Kapasiteyi daha fazla zorlayıp sistemi çökertme riskine girmeyelim; kullanıcıyı 'Yok' ile yormayalım." | Tavan 250'de kalır. Doğrulanamayan Shell istasyonları `hidden` yapılır; fiyat gelince otomatik geri döner. |
| 3 | **Moloz kapsamının daraltılması: ONAYLANDI.** "İstasyon LPG satmadığı için unknown görünen meşru satırlara dokunma." | Yalnızca 626 pasif istasyon + 966 fiyat satırı + 13.009 eski `fiyat_gecmisi` silinir. Aktifteki 1.092 `unknown` satıra **dokunulmaz**. |
| 4 | **Bağcılar-2 ve 26 kopya çifti: BİRLEŞTİR.** | B0 ölçümü → B2 birleştirme. |

---

## 0. ÖNCE ŞUNU SÖYLEMELİYİM

Talebiniz "Faz 0, 1, 2, 3'ün bittiğini biliyorum, kanıtla ve temizliğe geç" idi.
Ölçtüm. Sonuç ikiye ayrılıyor:

* **Faz 0, 1 ve 2 gerçekten kapalı.** Canlı veriyle doğrulandı, aşağıda kanıt tablosu var.
  Bu üç fazda açık kalan tek bir madde yok.
* **Faz 3 kapalı değil.** Yol haritası F3-1'i "101 kopya çifti → 0, doğrulandı" diye
  kapattı. **Bugün canlıda 26 aktif kopya çifti var** ve hepsi son bot koşularında
  güncellenmiş, yani canlı. Ayrıca F3-3 (Shell kapasitesi) "çözüldü" işaretli ama
  **178 aktif ve görünür Shell istasyonunun hâlâ hiçbir gösterilebilir fiyatı yok.**

Bu, "temizlikten önce kapanış onayı ver" talebinizin tam olarak işe yaradığı yer.
Moloz temizliğine başlasaydık, üretim hâlâ kopya üretirken çöpü süpürmüş olacaktık.

> **Kayıtlı ders (`fullet-olcmeden-duzeltme`):** aşağıdaki A1 bulgusunda bir kök-neden
> *hipotezim* var ama onu **kanıtlamadım**. Plan, düzeltmeyi yazmadan önce ölçmeyi
> ayrı bir adım olarak içeriyor. Aynı hatayı dördüncü kez yapmayacağız.

---

# BÖLÜM A — KAPANIŞ VE KANIT RAPORU

Tüm sayılar 3 Ağustos 2026, canlı Supabase (`xhkvlwecsacfjpbtyqcc`), salt-okunur
sorgularla alındı. Kod tarafı iddiaları dosya:satır ile doğrulandı.

## A.1 — Faz 0 (Görüş Aç): ✅ KAPALI

| Madde | İddia | Kanıt |
|---|---|---|
| 1 | CI alarm bayrağı kaldırıldı | `otopilot.yml:163` — `FULLET_FAIL_ON_BOT_ERROR` **set edilmiyor**, varsayılan `"1"` |
| 2 | Botlar dürüst çıkış kodu veriyor | `test_bot_exit_codes.py` (269 satır) yeşil |
| 3 | `records_written` kolonu | Canlıda dolu: son Shell koşusu `records_written=1266` |
| 4 | `ops_report`'un kör alarm kapatması silindi | `ops_report.py:217` artık yalnızca `source="ops_report"` kapatıyor; `bot:shell_bot.py` satırları yok |
| 5 | Ardışık hata çift sayımı | `telemetry.py` düzeltildi, `NON_FAILURE_STATUSES` ile birlikte |
| 6 | CI'da testler | `.github/workflows/tests.yml` — `pytest` + `flutter test` |

**Canlı doğrulama:** son 48 saatte 103 bot koşusu. Açık (`open`) tek bir
`system_alerts` kaydı **yok** — 12 alarmın hepsi `resolved`. Alarm mekanizması
ölü değil, çalışıp kapanmış: 2 Ağustos 23:11'de Shell için `warning` + `critical`
açılmış, düzeltmeden sonra kapanmış.

**Test durumu:** `pytest -q` → **119 passed**, 0 fail. (Yerelde koşturuldu.)

## A.2 — Faz 1 (Veri Hattı): ✅ KAPALI

`fiyatlar.son_dogrulama` kolonu canlıda mevcut ve yorumu doğru
("*Fiyatin kaynaktan son DOGRULANDIGI an... Tazelik bu kolona bakar*").
Tazelik eşikleri tek kaynakta: `freshness.py:47,50` → `FRESH_MAX_HOURS=12`,
`STALE_MAX_HOURS=48`.

**Salınımın durduğunun kanıtı — marka bazında, aktif istasyonlar:**

| Marka | Taze | Bayat | Bilinmiyor | Taze % |
|---|---|---|---|---|
| TotalEnergies | 1.642 | **0** | 11 | %99,3 |
| Opet | 1.006 | **0** | 2 | %99,8 |
| Petrol Ofisi | 240 | **0** | 0 | **%100** |
| BP | 111 | **0** | 0 | **%100** |
| Aytemiz | 70 | **0** | 2 | %97,2 |
| Türkiye Petrolleri | 140 | **0** | 16 | %89,7 |
| Shell | 2.321 | 97 | 1.061 | %66,7 |

Altı markada bayat **sıfır**. Faz 1 öncesi Opet/PO/Aytemiz/TP **%0 tazeydi**;
şimdi %89,7–%100. Sistemdeki tek bayat satır (97) Shell'e ait ve A.4'te ele alınıyor.

`quarantine_old_prices.py` env hatası düzeltilmiş: `run_all_bots.py:356`
`os.environ.copy()` kullanıyor ve dönüş kodu 365. satırda kontrol ediliyor.

## A.3 — Faz 2 (Uygulamadaki Yalan): ✅ KAPALI

Yol haritasının 14–20. maddelerinin altısı ✅, biri (17) ölçümle çürütülmüş ve
öyle belgelenmiş. Kod tarafında doğrulandı:

* `trustedPriceValueFor` artık yalnızca `price_alert_service.dart:74`'te —
  yani sadece bildirim eşiğinde. Haritadaki çifte havuz kaldırılmış
  (`modern_map_screen.dart:707`'deki yorum bunu belgeliyor).
* `utils/app_version.dart` tek sürüm kaynağı, `app_version_test.dart` kilitliyor.
* 6 Flutter test dosyası mevcut ve CI'da koşuyor.

## A.4 — Faz 3 (İstasyon Verisi): ❌ KAPALI DEĞİL — 3 açık bulgu

### 🔴 A1 — 26 aktif kopya çifti geri geldi (F3-1 "0" iddiası bugün geçerli değil)

```sql
-- 75 m içinde, aynı marka, ikisi de aktif:  26 çift
-- 75–150 m bandı (kasıtlı birleştirilmeyen): 18 çift
```

26 çiftin **hepsi** son bot koşularında güncellenmiş (`guncellenme_tarihi`
en yenisi bugün 13:23 — son Shell koşusu). Yani ölü kayıt değil, canlı kopya.
Örnekler:

| Marka | Kayıt 1 | Kayıt 2 | Mesafe |
|---|---|---|---|
| Shell | `ÇİNÇİN.` | `ÇİNÇİN.` | **0,0 m** |
| Shell | `MENEMEN ÇIKIŞI.` | `MENEMEN ÇIKIŞI.` | **0,0 m** |
| Shell | `Shell` | `ÇINARLI.` | 4,0 m |
| TotalEnergies | `YENİ SANAYİ (12T737)` | `Total Yeni Sanayi` | 8,0 m |
| Türkiye Petrolleri | `ADA ARİF PETROL` | `Türkiye Petrolleri` | 38,4 m |

**Kritik ayrım:** hepsinin `olusturulma_tarihi` **Nisan–Mayıs 2026**. Yani bunlar
birleştirmeden *sonra üretilmiş yeni kopyalar değil* — birleştirmenin **atladığı**
eski kayıtlar. Üretim tarafı (`StationProximityIndex`) muhtemelen doğru çalışıyor.

**Hipotezim (KANITLANMADI):** `merge_duplicate_stations.py:226` yalnızca
`aktif` istasyonları kümeliyor. Birleştirme koştuğunda bu kayıtlar **pasifti**,
sonra F3-2'nin yazma yolu (`database_writes.py:235` — dokunduğu her istasyona
`"aktif": True` yazıyor) onları aktifleştirdi. Sayılar bunu destekliyor:
aktif istasyon 2.636 → 2.728 (**+92**), üstelik arada 79 kayıt **silinmişken**
— yani ~171 istasyon pasiften aktife geçmiş.

Bu hipotez **B0 adımında ölçülecek**, düzeltme ondan sonra yazılacak.

### 🔴 A2 — 178 aktif ve görünür Shell istasyonunun hiç gösterilebilir fiyatı yok

| Marka | Aktif+görünür istasyon | Hiç gösterilebilir fiyatı yok | Taze fiyatı yok |
|---|---|---|---|
| **Shell** | 963 | **178 (%18,5)** | **224 (%23,3)** |
| TotalEnergies | 808 | 0 | 0 |
| Opet | 503 | 0 | 0 |
| Petrol Ofisi | 80 | 0 | 0 |
| Türkiye Petrolleri | 70 | 0 | 0 |
| BP | 37 | 0 | 0 |
| Aytemiz | 35 | 0 | 0 |

Bu 178 istasyonun Motorin ve Kursunsuz 95 satırları `unknown` ve
**son doğrulama 31 Temmuz 22:26** — üç gündür dokunulmamış.
Kullanıcı haritada bu pinlere basınca **"Yok"** görüyor.

Bu **moloz değil**, canlı bir doğruluk boşluğu. F3-3 tavanı 150→250 yaptı
(kapsama %85,6'ya çıktı) ama Shell'in ilçe listesi 250'den uzun; kuyruktaki
ilçeler hiç sıraya gelmiyor. Faz 3 bunu "çözüldü" olarak işaretlememeliydi.

### 🟡 A3 — 232 istasyon `aktif=true` **ve** `visibility_status='hidden'`

Kendi kod tabanınız bunu risk sayıyor: `backend_health_check.py:217`
tam bu kombinasyonu `hidden_risk` olarak bayraklıyor. Ters yönde de 354 satır var
(`aktif=false` + `visible`). İki bayrak birbirinden bağımsız yazılıyor ve
tutarlılık hiçbir yerde zorlanmıyor.

| | `visible` | `low_priority` | `hidden` |
|---|---|---|---|
| **aktif** | 1.444 | 1.052 | **232 ⚠️** |
| **pasif** | 354 ⚠️ | 0 | 272 |

### 🟡 A4 — Her istasyon botu koşusu istasyonları `low_priority`'ye düşürüyor

`database_writes.py:235`:
```python
updates.append({"id": station_id, **payload, "visibility_status": "low_priority", "aktif": True})
```
Koşul yok — `visible` bir istasyon bota her dokunulduğunda `low_priority`'ye
**geri düşüyor**. Canlıda 1.052 istasyon bu durumda. Bu, 21. maddenin
(`low_priority` kararı) neden acil olduğunu gösteriyor: mekanizma hem ölü
(uygulama `low_priority`'yi normal gösteriyor) hem de sürekli tetikleniyor.

### 🟡 A5 — 9 sayfalamada `ORDER BY` yok (gizli risk, hasar KANITLANMADI)

`merge_duplicate_stations.py:84`, `matching.py:322`, `database_writes.py:348`,
`ops_report.py:74`, `backend_health_check.py:93`, `sanity_gate.py:60`,
`shell_bot.py:80`, `quarantine_unverified_live_data.py:65`,
`clean_duplicate_stations.py:48` — hepsi `.range(start, start+999)` ile sayfalıyor,
hiçbiri `.order()` kullanmıyor.

`ORDER BY` olmadan sayfalama Postgres'te **garantisizdir**: eşzamanlı `UPDATE`'ler
satırları heap'te taşıdığında bir satır iki kez gelebilir ya da hiç gelmeyebilir.
Bu tablolara botlar sürekli yazıyor. **Ölçtüm: tek bir snapshot içinde bugün
kayıp yok (3.354/3.354).** Yani bu bir *teşhis* değil, kapatılması gereken bir
*risk*. Düzeltmesi tek satır (`.order("id")`), maliyeti sıfır.

## A.5 — KAPANIŞ HÜKMÜ

| Faz | Hüküm |
|---|---|
| Faz 0 — Görüş aç | ✅ **KAPALI** — kanıtlı |
| Faz 1 — Veri hattı | ✅ **KAPALI** — kanıtlı |
| Faz 2 — Uygulama | ✅ **KAPALI** — kanıtlı |
| Faz 3 — İstasyon verisi | ❌ **AÇIK** — A1, A2 gerçek; A3, A4, A5 kapatılmalı |

"Sistemde hiçbir açık kalmadı" onayını **veremem**. Bu planın B ve C bölümleri
tamamlandığında verebilirim.

---

# BÖLÜM B — UYGULAMA PLANI

Sıra kasıtlı: **önce üretimi durdur, sonra mevcudu temizle, en son kozmetik.**
Ters sırada temizlik yaparsak bir sonraki bot koşusu çöpü geri koyar.

## B0 — ÖLÇÜM (düzeltme yazmadan önce) — ~1 saat

Tek amacı A1'in kök nedenini **kanıtlamak**. Hiçbir yazma yok.

1. `merge_duplicate_stations.py`'ı **açık dry-run** ile koştur
   (`FULLET_ALLOW_DB_WRITE` açıkça `0`). Beklenen: 26 çifti bulmalı.
   * **Bulursa** → hipotez doğru: kayıtlar birleştirme anında pasifti,
     sonradan aktifleşti. Düzeltme = B2 (yeniden koştur) + B1 (tekrarı önle).
   * **Bulamazsa** → hipotez yanlış, kümeleme mantığında ayrı bir hata var;
     plan durur ve size yeni ölçümle dönerim.
2. Aynı koşuda birleştirme zamanı (`aba496b` commit'i) ile 171 istasyonun
   aktifleşme zamanını `guncellenme_tarihi` üzerinden karşılaştır.

**Kapı:** B0 sonuçlanmadan B1'e geçilmez.

## B1 — ÜRETİMİ DURDUR (kopya + durum bayrakları) — ~yarım gün

3. **`merge_duplicate_stations.py` pasif kayıtları da görsün.**
   `:226`'daki `and s.get("aktif")` filtresini kaldır; hayatta kalan seçiminde
   aktif olan öncelikli olsun. Böylece "sonradan aktifleşen pasif kopya"
   sınıfı tekrar oluşamaz.
4. **`aktif` / `visibility_status` tutarlılığını zorla.** (A3)
   Tek bir yardımcı (`db_utils.station_visibility_payload`) iki alanı birlikte
   yazsın; `aktif=false` ⇒ `hidden`, `aktif=true` ⇒ `visible|low_priority`.
   Mevcut 232 + 354 tutarsız satır tek seferlik SQL ile hizalanır.
5. **`low_priority` düşürmesini koşullu yap.** (A4 + eski madde 21 — aşağıda)
6. **9 sayfalamaya `.order("id")` ekle.** (A5) Mekanik, risksiz.

**Doğrulama kapısı:** Bir tam bot turu koştur. Sonrasında ≤75 m aktif kopya
çifti **artmamalı** ve `aktif+hidden` sayısı **0** olmalı.

## B2 — MEVCUT KOPYALARI BİRLEŞTİR — ~1 saat

7. Düzeltilmiş `merge_duplicate_stations.py`'ı **önce dry-run**, çıktıyı size
   gösterdikten **sonra** yazma modunda koştur.
8. **Bağcılar-2 (talebinizin 4. maddesi)** aynı koşuda çözülür:
   `BAĞCILAR-2 (12T951)` ↔ `Total Bağcılar-2`, 146 m, ikisi de aktif,
   ikisinde de 2 fiyat satırı. 75–150 m bandındaki "biri jenerik isimli"
   kuralına **`Total Bağcılar-2` jenerik sayılmadığı için** takılmıyor.
   Bunu elle birleştireceğim (ayrı bulanık eşleştirme kuralı yazmak,
   tek satır için kırılgan bir mekanizma eklemek olurdu).

**Doğrulama:** ≤75 m aktif kopya çifti = **0**, Bağcılar için tek kayıt.

## B3 — SHELL KAPSAMA BOŞLUĞU (A2) — ~yarım gün

Bu, planın en çok kullanıcı etkisi olan maddesi: 178 istasyon = haritada 178 "Yok".

9. **Önce ölç:** Shell'in ilçe listesi kaç hedef? 250 tavanı listenin yüzde
   kaçını kapsıyor? Öncelik sırası hangi ilçeleri kuyrukta bırakıyor?
10. **KARAR: seçenek (b) — gizle.** (Kullanıcı onayı, 3 Ağustos.) Tavan 250'de
    kalır, kapasite zorlanmaz. Hiç gösterilebilir fiyatı olmayan istasyon
    `hidden` yapılır — "Yok" göstermektense göstermemek daha dürüst.

    **Kritik tasarım kısıtı:** gizleme **geri döndürülebilir** olmalı. Shell'in
    hedef listesi dönerek ilerliyor; bugün kuyrukta olan ilçe yarın öne geliyor.
    Fiyat gelen istasyon **otomatik** `visible`'a dönmeli, yoksa her tur kalıcı
    olarak istasyon kaybederiz. Bu yüzden gizleme ayrı bir script değil,
    yazma yolunun (`database_writes`) bir parçası olacak.

> **Not — bu, A2'nin kök nedenini çözmez, belirtisini gizler.** 178 istasyon
> hâlâ fiyatsız kalacak, sadece haritada görünmeyecek. Gerçek çözüm Shell'in
> hedef kapsamasını artırmaktır ve ayrı bir iş olarak açık kalıyor
> (Faz 4 / yeni istasyon toplama işiyle birlikte ele alınmalı).

## B4 — MOLOZ VERİ TEMİZLİĞİ (talebinizin 3. maddesi) — ~2 saat

**Önce sayıları düzeltmem gerekiyor.** Yol haritasındaki "797 pasif satır ve
1.065 unknown fiyat" rakamları eskidi. Bugünkü gerçek:

| | Sayı | Karar |
|---|---|---|
| Pasif istasyon | **626** | 🗑️ Sil |
| Pasif istasyonlara bağlı fiyat satırı | **966** | 🗑️ Sil (CASCADE) |
| Aktif istasyonlarda `unknown` fiyat | **1.092** | ⚠️ **SİLME** — aşağıya bak |
| — bunun LPG olanı | 698 | ✅ Meşru: o istasyon LPG satmıyor |
| — bunun Shell Motorin/K95 olanı | 394 | 🔴 **A2 boşluğu** — moloz değil, eksik veri |
| `fiyat_gecmisi` 90 günden eski | 13.009 | 🗑️ Sil (öksüz satır: 0) |

**Önemli uyarı:** "1.065 unknown fiyatı sil" talimatını olduğu gibi uygularsak
**yanlış veri silmiş oluruz.** Aktifteki 1.092 `unknown` satırın 698'i
"bu istasyon LPG satmıyor" bilgisidir — silinirse bot bir sonraki koşuda
zaten geri yazar (boş yazma trafiği), ayrıca uygulamanın "bu yakıt yok"
ayrımı bozulur. 394'ü ise A2'nin ta kendisi — silmek boşluğu **gizlemek** olur.

Bu yüzden temizlik kapsamı: **626 pasif istasyon + 966 fiyat satırı +
13.009 eski geçmiş satırı.** Diğerleri düzeltilecek, silinmeyecek.

11. Silmeden önce yedek: silinecek satırların `id`'lerini dosyaya döküp size sunarım.
12. `scraper/purge_inactive_stations.py` — dry-run varsayılan, favori/alarm
    kontrolü yapar (`ON DELETE CASCADE` var), sonra siler.
13. `fiyat_gecmisi` budaması SQL ile; 90 gün eşiği `price_trend_sparkline.dart`'ın
    ihtiyacından uzun (kontrol edilecek).

## B5 — ERTELENEN 21–25. MADDELER (talebinizin 5. maddesi)

Önce **ne olduklarını** açıklıyorum, sonra planı veriyorum.

### Madde 21 — `low_priority` kararı *(S3-3)*
**Ne:** pg_cron JOB 3, 7 gündür güncellenmemiş istasyonları
`visible → low_priority` düşürüyor. Ama uygulama `station.dart:90`'da
`low_priority`'yi **görünür** sayıyor, RPC de kabul ediyor. Yani güvenlik
mekanizması kurulmuş, hiçbir yere bağlanmamış.
**Yeni bilgi:** A4'te bulduğum gibi durum daha kötü — `database_writes.py:235`
her istasyon botu koşusunda dokunduğu istasyonu `low_priority`'ye düşürüyor.
Canlıda 1.052 istasyon böyle. `isLowPriority` yalnızca `station_bottom_sheet.dart:172`'de
bir uyarı bandı için kullanılıyor.
**Plan:** `low_priority`'yi **gerçek** yap — marker'da soluklaştır ve
"en ucuz" yarışından çıkar; `database_writes.py:235`'teki koşulsuz düşürmeyi kaldır.
(Alternatif — JOB 3'ü silmek — daha az iş ama gerçek bir koruma mekanizmasını atardı.)

### Madde 22 — Push token temizliği *(S3-4)*
**Ne:** `auto_price_staleness.sql:79-89` "90 gündür **kullanılmamış** token'ları sil"
diyor, kod `olusturulma_tarihi < NOW() - 90 days` yazıyor — yani 90 günlük
**sadık** kullanıcının token'ını siliyor. Doğru kolon (`son_guncelleme`) tabloda mevcut.
**Plan:** Madde 23'e bağlı. Push kaldırılırsa bu madde de düşer.

### Madde 23 — Push altyapısı kararı *(S3-5)*
**Ne:** Uçtan uca kopuk. Ölçtüm: `push_tokens` tablosunda **0 satır**;
Flutter'da `firebase_messaging` **yok**, `push_tokens`'a tek bir INSERT yok;
Edge function `fiyat-push` yalnızca Expo token'ı gönderiyor. `NotificationService`
ise **yerel** bildirim (hatırlatıcı, fiyat alarmı) — o çalışıyor ve kalmalı.
Ölü olan yalnızca **uzak push** yüzeyi.
**KARAR: KALDIR** (kullanıcı onayı, 3 Ağustos). Kapsam: `fiyat-push` Edge Function,
`push_tokens` tablosu, `send_summary_push`, `summary_push.py`, `FULLET_PUSH_*`
ortam değişkenleri, `auto_price_staleness.sql`'deki token temizlik job'u.
**KALIR:** `NotificationService` ve tüm yerel bildirimler (hatırlatıcı, fiyat alarmı)
— onlar cihaz üstünde çalışıyor ve ölü değil. Bu, 22. maddeyi de kapatır.

### Madde 24 — SQL doğruluk kaynağını teke indirme *(S3-6)*
**Ne:** `get_nearby_stations` dört ayrı dosyada tanımlı; `database/` (30 dosya)
ile `supabase/migrations/` (5 dosya) iki ayrı gerçek kaynağı. `database/README.md`
bunu zaten itiraf ediyor ("*gerçek şema geçmişi burada... bu durum kırılgan*").
Riski: yanlış sırada çalıştırma iki overload bırakır → PostgREST çağrıyı çözemez →
uygulama sessizce tüm-ülke fallback'ine düşer.
**Plan:** Fonksiyon tanımlarını migrations'a taşı, `database/` yalnızca tek seferlik
onarım scriptleri kalsın, README'yi buna göre yaz. `20260708120100`'ün
`20260708130000` tarafından ezildiğini dosya başına yaz.

### Madde 25 — Sessiz `catch` bloklarına iz *(S3-10)*
**Ne:** `supabase_service.dart`'ta `upsertUserProfile`, `addFavorite`,
`removeFavorite` hatayı tamamen yutuyor. Favori eklenmezse kullanıcı yerelde
görüyor, başka cihazda göremiyor, hiçbir iz kalmıyor.
**Plan:** `debugPrint` + Crashlytics kaydı. Küçük ve net.

### 21–25 uygulama sırası
`23 → 22` (push kaldırılınca 22 düşer) → `21` → `25` → `24`.
24 en sona, çünkü şema dosyalarına dokunmak diğer adımların doğrulamasını bulandırır.

## B6 — KOD TEMİZLİĞİ (talebinizin 2. maddesi) — ~yarım gün

**En sona koydum bilinçli olarak:** ölü kodu şimdi silersem, B1–B5'te
"bu neden buradaydı?" bilgisini kaybederiz. Ayrıca A2/A3 düzeltmeleri
bazı dosyalara zaten dokunacak.

**Kanıtlanmış ölü kod (referansı sıfır — grep ile doğrulandı):**

| Ne | Nerede | Kanıt |
|---|---|---|
| `clean_duplicate_stations.py` | 110 satır, tam dosya | Hiçbir yerden çağrılmıyor; `merge_duplicate_stations.py` yerine geçti |
| `quarantine_unverified_live_data.py` | 90 satır, tam dosya | Hiçbir yerden çağrılmıyor |
| `summary_push.py` | 15 satır, tam dosya | CLI sarmalayıcı, hiçbir workflow çağırmıyor |
| `_station_inventory_coord_key` | `matching.py:290-301` | Faz 3'te `StationProximityIndex` ile değiştirildi, tanım kaldı |

**İncelenecek (silme kararı okuma sonrası):**
* `matching.py`'de iki eşleştirme yolu (`_station_targets` vs `_load_brand_stations`)
  hâlâ paralel duruyor. Yol haritası madde 12'yi ölçümle **reddetmişti** —
  o kararı bozmayacağım, ama iki yolun sınırını yorumla netleştireceğim.
* `docs/FULLET_PRD.md.txt` — `.txt` uzantılı, muhtemelen artık geçersiz.
* `database/` içindeki `admin_observability_repair*.sql` üçlemesi ve
  `*_simple.sql` varyantları — tek seferlik onarım kalıntısı.
* Kök dizindeki 11 `.md` denetim dosyası: bir kısmı (`FULLET_RELEASE_*`,
  `PLAY_STORE_READINESS`) pazarlama iptali sonrası bayat.
  **Silmeyeceğim** — arşiv değeri var; başlıklarına "BAYAT (tarih)" bandı koyacağım.

**Yapmayacaklarım (kasıtlı):**
* Çalışan mimariyi "daha temiz" diye yeniden yazmak. Ölçülmüş, kanıtlanmış,
  testlerle kilitlenmiş kod tabanına estetik gerekçeyle dokunmak, bu projede
  tam olarak pahalıya mal olan şey.
* `modern_map_screen.dart`'ı (2.707 satır) bölmek. Büyük ama çalışıyor ve
  Faz 2'de yeni doğrulandı. Bölmek regresyon riski, doğruluk kazancı sıfır.

## B7 — REGRESYON KİLİDİ — ~2 saat

Her yeni bulgu için bir test — yoksa aynı hata geri gelir (A1 tam olarak
bunun kanıtı: F3-1 test edilmediği için sessizce geri geldi).

* Pasiften aktife dönen kopya birleştirmede yakalanıyor mu? (A1)
* `aktif=false` yazan her yol `hidden` de yazıyor mu? (A3)
* `visible` bir istasyon bot koşusunda `low_priority`'ye düşmüyor mu? (A4)
* Sayfalayan her fonksiyon `.order()` çağırıyor mu? (A5 — statik test)
* Pasif istasyon temizliği aktif istasyona dokunuyor mu? (B4)

---

# C. SIRALAMA, SÜRE VE KAPILAR

| Adım | İş | Süre | Kapı |
|---|---|---|---|
| B0 | A1 kök nedenini ölç | 1 saat | **Hipotez doğrulanmazsa plan durur, size dönerim** |
| B1 | Üretimi durdur (kopya, bayraklar, sayfalama) | 0,5 gün | Bir tam bot turu sonrası kopya artmamalı |
| B2 | Mevcut kopyaları birleştir + Bağcılar-2 | 1 saat | ≤75 m aktif kopya çifti = 0 |
| B3 | Shell kapsama boşluğu (178 istasyon) | 0,5 gün | Ölç → karar → uygula |
| B4 | Moloz veri temizliği | 2 saat | Yedek alınmadan silme yok |
| B5 | 21–25. maddeler | 0,5 gün | Her madde ayrı commit |
| B6 | Kod temizliği | 0,5 gün | `pytest` + `flutter test` yeşil |
| B7 | Regresyon kilidi | 2 saat | CI yeşil |
| **Toplam** | | **~3 gün** | |

**Her adım ayrı commit.** Her yazma işleminden önce dry-run çıktısını size gösteririm.

---

# D. ONAYINIZI BEKLEYEN KARARLAR

Bu üçü sizin kararınız; planı ona göre kesinleştireceğim:

1. **Push altyapısı (madde 23):** kaldıralım mı, tamamlayalım mı?
   *Önerim: kaldır.* `push_tokens` tablosunda 0 satır var, Flutter tarafı hiç bağlanmamış.
2. **Shell'in 178 fiyatsız istasyonu (A2):** kapasiteyi mi zorlayalım (a),
   yoksa doğrulanamayanı uygulamada gizleyelim mi (b)?
   *Önerim: önce ölç, sonra karar ver — B3/9. adım.*
3. **Moloz kapsamı:** Aktifteki 1.092 `unknown` satıra **dokunmuyorum**
   (698'i meşru "bu yakıt yok" bilgisi, 394'ü A2 boşluğu). Yalnızca
   626 pasif istasyon + 966 fiyat + 13.009 eski geçmiş satırı silinecek.
   Bu daraltmayı onaylıyor musunuz?

---

## EK — Güvenlik notu (planın dışında, bilginiz olsun)

Supabase advisor `public.spatial_ref_sys` tablosunda RLS'in kapalı olduğunu
bildiriyor. Bu **PostGIS'in kendi sistem tablosu**, sizin veriniz değil ve
salt-okunur referans verisi (8.500 koordinat sistemi tanımı). Bilinen bir
Supabase uyarısıdır, `database/postgis_spatial_ref_sys_rls.sql` dosyanız
konuyu zaten ele almış. **Acil değil, bu planın parçası değil** — ama
raporda gördüğüm için not düşüyorum.
