# Fullet — Taban Ölçüm Raporu (W1)

**Durum:** ✅ KAPANDI (7 Ağustos 2026) — W1 görevi tamamlandı.
**Tarih:** 2026-08-07
**Hazırlayan:** [isim]
**Kapsam:** Google Play Console + Firebase Analytics (GA4) — tek seferlik anlık durum fotoğrafı.
**Not:** 1.0.3+6 sürümü dün (6 Ağustos) yayına alındı. Play Console verileri 24-48 saat
gecikmeli işlenir; bu raporun bazı satırları hâlâ önceki sürümün trafiğini içerebilir.
Bir sonraki haftalık panoda (§11.4) bu sapma normalize olacaktır.

---

## A. Play Console — Store performansı

| Metrik | Kaynak (Play Console) | Değer | Not |
|---|---|---|---|
| Kurulum (son 7 gün) | Statistics → Installs | 3 | |
| Kurulum (son 30 gün) | Statistics → Installs | 28 | Kontrol panelinden alındı |
| Kaldırma oranı (uninstall) | Statistics → Uninstalls | %15,79 | Hedef: < %30 |
| Store conversion rate | Store Performance → Overview | %47 | Hedef: ≥ %25 |
| Store'a ziyaretçi sayısı | Store Performance → Overview | 45 | |
| İlk 10 arama terimi + payı | Store Performance → Search terms performance | | Marka araması payı ayrıca not edilsin |
| Ülke kırılımı (top 5) | Statistics → Add dimension → Country | | |
| Cihaz/Android sürüm kırılımı | Statistics → Add dimension → Device/OS | | |
| Ortalama puan | Quality / Reviews | 5.0 | Kırmızı bayrak: < 4,0 |
| Toplam yorum sayısı | Reviews | | |

## B. Firebase Analytics (GA4) — Ürün kullanımı

| Metrik | Kaynak (GA4) | Değer | Not |
|---|---|---|---|
| DAU | Etkinlik/Kullanıcılar, 1 günlük aralık | 4 | |
| MAU | Etkinlik/Kullanıcılar, 28-30 günlük aralık | 49 | |
| DAU/MAU (yapışkanlık) | Yaşam döngüsü → Etkileşim → Genel Bakış | %8,16 | Hedef: ≥ %20 |
| D1 retention | Yaşam döngüsü → Elde Tutma | Veri Yetersiz | Kırmızı bayrak: < %20 |
| D7 retention | Yaşam döngüsü → Elde Tutma | Veri Yetersiz | Hedef: ≥ %15 |
| `onboarding_completed` ÷ `onboarding_skipped` | Etkinlikler | %30,7 | Hedef: ≥ %60 tamamlama |
| `garage_vehicle_set` (benzersiz kullanıcı) | Etkinlikler | 9 UU | Hedef: ≥ %35 · Kırmızı bayrak: < %20 |
| `station_tapped` / oturum | Etkinlikler | %78,8 | Hedef: ≥ %70 (kuruludan) |
| `directions_requested` haftalık UU ★ | Etkinlikler | 6 UU | **Kuzey yıldızı** · Hedef: ≥ %40 |
| `fuel_type_changed` dağılımı | Etkinlikler | 25 UU (85 kez) | Motorin ↑ = P1/P3 sinyali |
| `brand_filter_changed` kullanan UU | Etkinlikler | 19 UU | |
| `smart_selection_seen` UU | Etkinlikler | 0 | |
| `favorite_toggled` UU | Etkinlikler | 1 UU | |
| `search_performed` sayısı | Etkinlikler | 93 | |

## C. Dönüşüm hunisi (GA4 → Keşif → Huni Keşfi ile üretilir)

```
Play sayfası görüntüleme →  %100   (hedef ≥ %25)
Kurulum                   →  %47   (hedef ≥ %85 ilk açılış)
Onboarding tamamlama      →  %30,7   (hedef ≥ %60)
Garaj doldurma            →  %18,3   (hedef ≥ %35) ★ en kritik eşik
İstasyon inceleme         →  %34,6   (hedef ≥ %70)
Yol tarifi (kuzey yıldızı) →  %12,2   (hedef ≥ %40)
D7 geri dönüş             →  Veri Yetersiz   (hedef ≥ %15)
```

**En zayıf basamak:** Onboarding Tamamlama (%30,7) ve Garaj Doldurma (%18,3). Kullanıcıların büyük kısmı onboarding'i "Atla" (skip) ile geçmiş (27 kişi) ve garajını doldurmamış. Sonraki adımda tüm pazarlama odağı burası olacak.

## D. Kırmızı bayrak kontrolü (§11.6)

| Sinyal | Eşik | Bugünkü değer | Durum |
|---|---|---|---|
| Kaldırma oranı | > %40 | %15,79 | [x] Normal / [ ] Alarm |
| D1 | < %20 | Veri Yetersiz | [ ] Normal / [ ] Alarm |
| Play puanı | < 4,0 | 5,0 | [x] Normal / [ ] Alarm |
| Garaj doluluk | < %20 | %18,3 | [ ] Normal / [x] Alarm |

---

**Sonraki adım:** Bu rapor her Pazartesi §11.4'teki haftalık pano ile güncellenecek;
ilk defa dolduruluyor olması nedeniyle bu hafta trend değil, yalnızca gün 0 fotoğrafı
kaydedilmiş olacak.

**Kök neden bulundu ve kapatıldı:** Onboarding "Atla" butonu garaj adımını da
atlıyordu. Düzeltme 11 Ağustos 2026'da 1.0.4+7 ile yayınlandı; kod kanıtı ve
bilinçli test kapsamı kararı `RELEASE_NOTES.md` §1.0.4'e taşındı.

**Açık kalan (küçük, W1 kapanışını engellemiyor):** Tablo A'da 3 hücre hâlâ boş —
ilk 10 arama terimi, ülke/cihaz kırılımı, toplam yorum sayısı. Bunlar tamamlayıcı
veri; üst huninin sağlıklı olduğu (conversion %47, uninstall %15,8, puan 5,0) zaten
diğer satırlarla doğrulandı. W2'de ASO çalışmasına başlarken (arama terimi verisi
doğrudan kullanılacağı için) bu 3 hücre o zaman dolduralım.
