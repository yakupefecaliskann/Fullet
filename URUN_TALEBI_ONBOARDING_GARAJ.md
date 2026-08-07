# Ürün Talebi — Onboarding "Atla" garaj adımını da atlıyor

**Tarih:** 2026-08-07 · **Kaynak:** W1 taban ölçüm raporu (`baseline.md`) huni analizi
**Durum:** Backlog — bir sonraki sürüm döngüsünde ele alınacak (bugün kod tarafına
dokunulmadı, karar verildi).

## Bulgu

W1 baseline'da `onboarding_completed` %30,7, `garage_vehicle_set` %18,3 ile kırmızı
alarm eşiğinin altında çıktı. Kod incelemesi bu ikisinin **tek bir sorun** olduğunu
gösterdi:

- `onboarding_screen.dart:94-106` — "Atla" butonu 3 sayfanın hepsinde sağ üstte, en
  görünür konumda.
- `onboarding_screen.dart:59-67` (`_skip`) — Atla'ya basınca `openGarageOnStart`
  hiç `true` olmuyor → garaj bottom sheet'i hiç açılmıyor. Atla, hem tanıtımı hem
  araç girme adımını aynı anda iptal ediyor.
- `onboarding_screen.dart:47-57` (`_complete`) — onboarding'i bitirenlerde
  `openGarageOnStart: true` ile harita açılıyor, garaj modalı otomatik tetikleniyor
  (`modern_map_screen.dart:145-150`, `:1447-1450`).
- Matematik: 12 kişi onboarding'i tamamlamış, 9 kişi araç girmiş → tamamlayanların
  **%75'i** araç giriyor. Garaj deneyiminin kendisi iyi çalışıyor; sorun oraya hiç
  ulaşılmaması.
- Garaj adımı zaten tamamen opsiyonel bir bottom sheet (`garage_modal.dart:17-24`,
  dışarı tıklayıp kapatılabiliyor) — zorunlu hale getirmeye gerek yok, sadece
  gösterilmesi gerekiyor.
- 2. sayfadaki araç değeri anlatımı tek cümleyle sınırlı: *"Aracını ekle, Fullet
  sadece ucuzu değil en mantıklı durağı da bulsun."*

## Önerilen düzeltme (küçük, düşük riskli)

1. `_skip` davranışını ayır: tanıtım sayfalarını atlasın ama `openGarageOnStart`
   yine de `true` olsun — kullanıcı tanıtımı geçse bile, dönüşümü zaten yüksek olan
   garaj adımını görmeye devam etsin.
2. 2. sayfadaki copy'yi güçlendir — tek cümle yerine somut fayda ("LPG'li aracın
   varsa farklı istasyon önerebiliriz" gibi segment bazlı bir örnek).

## Örneklem uyarısı

Bu hafta n çok küçük (28 kurulum/30 gün, 12 onboarding tamamlama). Yön doğru
görünüyor ama düzeltme sonrası bir hafta gözlemlemeden kesin sonuç çıkarma.

## İlgili

`FULLET_GROWTH_STRATEGY.md` §11.3 (huni okuma kuralı), §11.6 (kırmızı bayraklar),
`baseline.md` (W1 taban ölçüm).
