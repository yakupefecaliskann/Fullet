# Fullet — Sürüm Notları

## 1.0.4 (versionCode 7) — Ağustos 2026

---

### 📋 Play Console "Yenilikler" alanına yapıştırılacak metin

```text
Küçük ama önemli bir düzeltme: tanıtım ekranını "Atla" ile geçenlerde de artık
Garajım paneli açılıyor, aracını eklemek bir dokunuş uzağında. Akıllı öneri
metnini de netleştirdik: LPG'li veya dizel aracın varsa sana en uygun
istasyonu gösteririz.
```

### 🎯 Uzun sürüm (iç kullanım)

W1 taban ölçüm raporunda (`docs/baseline.md`) `garage_vehicle_set` %18,3 ile kırmızı
alarm eşiğinin altında çıktı. Kök neden koddaydı: onboarding'te "Atla"ya
basanlarda `openGarageOnStart` bayrağı hiç set edilmiyordu, bu yüzden Garajım
paneli kimseye gösterilmiyordu. Onboarding'i bitirenlerin zaten **%75'i** araç
giriyor — panel iyi çalışıyor, sorun ona hiç ulaşılamamasıydı.

- `_skip()` artık haritaya `openGarageOnStart: true` ile geçiyor; Atla artık
  yalnızca tanıtım sayfalarını atlıyor, garaj adımını atlamıyor.
- 2. sayfadaki araç-değeri metni somut bir örnekle (LPG/dizel eşleşmesi)
  güçlendirildi.

#### Kök neden — kod kanıtı

Bulgu 7 Ağustos 2026'da W1 huni analizinden çıktı; `onboarding_completed` %30,7
ve `garage_vehicle_set` %18,3'ün **tek bir sorun** olduğu kod okumasıyla saptandı:

- `onboarding_screen.dart` — "Atla" butonu 3 sayfanın hepsinde sağ üstte, en
  görünür konumda duruyordu.
- `_skip()` — Atla'ya basınca `openGarageOnStart` hiç `true` olmuyordu, garaj
  bottom sheet'i hiç açılmıyordu. Atla, tanıtımı ve araç girme adımını aynı anda
  iptal ediyordu.
- `_complete()` — onboarding'i bitirenlerde `openGarageOnStart: true` ile harita
  açılıyor, garaj modalı otomatik tetikleniyordu (`modern_map_screen.dart`).
- Garaj adımı zaten tamamen opsiyonel bir bottom sheet (`garage_modal.dart`,
  dışarı tıklayıp kapatılabiliyor) — zorunlu hale getirmeye gerek yoktu, sadece
  gösterilmesi gerekiyordu.

#### Test notu (bilinçli kapsam kararı)

`flutter analyze` temiz, 45 unit testin tamamı geçiyor. Bu ekrana özgü otomatik
**widget testi eklenmedi**: `AnalyticsService`, `FirebaseAnalytics.instance`
üzerinden statik bir singleton'a bağlı ve repoda hiç widget-test altyapısı yok.
Doğru Firebase mock'unu (Pigeon kanalı) kurmak, 2 satırlık bir yönlendirme
düzeltmesine göre orantısız bir altyapı yatırımı olurdu. Değişiklik bunun yerine
gerçek cihazda elle doğrulandı (Atla → garaj paneli açılıyor).

#### Örneklem uyarısı

Düzeltme yapıldığında n çok küçüktü (28 kurulum/30 gün, 12 onboarding tamamlama).
Yön doğru görünüyor ama etkisi hakkında kesin sonuç çıkarmadan önce yayın
sonrası en az bir hafta gözlemlenmeli.

### 🔧 Teknik not — AAB hedef platformları

Bu derlemede `--target-platform android-arm,android-arm64` kullanıldı;
**android-x64 hariç tutuldu**. Sebep: bu makinede Windows'un Uygulama Denetimi
ilkesi, x64 AOT derleyicisini (`gen_snapshot.EXE`) çalıştırmayı reddetti.
Gerçek Android telefonlarda x86_64 pratikte hiç kullanılmadığı için (yalnızca
bazı emülatör/Chromebook senaryoları) bu dışlama üründe bir kayıp yaratmıyor,
ama gelecekteki her sürümde aynı bloklamayla karşılaşılacaksa
`scripts/release_check.ps1`'in build satırına da bu bayrak eklenmeli — ya da
Windows tarafındaki ilke kalıcı olarak çözülmeli.

---

## 1.0.3 (versionCode 6) — Ağustos 2026

---

### 📋 Play Console "Yenilikler" alanına yapıştırılacak metin

> Play Console'un **What's new** alanı dil başına **500 karakterle** sınırlıdır.
> Aşağıdaki metin bu sınıra göre yazıldı (≈470 karakter).

```text
Bu sürümde Fullet çok daha geniş bir haritayla geliyor.

• 6.000'i aşkın istasyon: envanter iki katından fazla büyüdü, çok daha fazla ilçede
  yakınındaki istasyonu görüyorsun.
• Tertemiz harita: aynı istasyonun tekrar eden kayıtları birleştirildi, kopya kalmadı.
• Şeffaf fiyat: her fiyatın kaynağı artık açıkça yazıyor — "Ankara geneli ilan fiyatı"
  gibi. Doğrulayamadığımız fiyatı göstermiyoruz.
• Android 16 uyumu, daha akıcı harita ve hata düzeltmeleri.
```

---

### 🎯 Uzun sürüm (store listing / basın / iç kullanım)

**Fullet 1.0.3 — Daha geniş harita, daha dürüst fiyat**

Bu sürümde tek bir şeye odaklandık: **haritadaki verinin doğru ve eksiksiz olması.**

#### ⛽ Envanter iki katından fazla büyüdü

Fullet artık Türkiye genelinde **6.000'i aşkın** akaryakıt istasyonu tanıyor. Opet,
Petrol Ofisi ve Aytemiz envanterleri baştan sona yeniden toplandı; daha önce yalnızca
birkaç yüz istasyonun göründüğü markalarda kapsam binlere çıktı. Küçük ilçelerde ve
şehirlerarası yollarda artık çok daha fazla seçenek görüyorsun.

#### 🧹 Kopya kayıtlar tarihe karıştı

Aynı istasyonun haritada iki-üç kez görünmesine yol açan yinelenen kayıtlar
birleştirildi ve kopya üretiminin kaynağı kapatıldı. Harita artık **sıfır kopya** ile
çalışıyor: gördüğün her pin gerçek ve tek bir istasyon.

#### 🔍 Fiyatın kaynağı artık açıkça yazıyor

En önemli yenilik bu. Türkiye'de akaryakıt fiyatları büyük ölçüde **il bazında** ilan
edilir; markanın tek tek istasyon fiyatı yayınlaması istisnadır. Eskiden ekranda
"Doğrulanmış fiyat" yazıyordu — bu, istasyona özel bir kesinlik ima ediyordu.

Artık her fiyatın yanında kapsamı yazıyor:

- **"✓ Ankara geneli ilan fiyatı"** → markanın o il için ilan ettiği fiyat
- **"✓ İstasyondan doğrulandı"** → gerçekten o istasyona ait fiyat

Ve şu kuralı değiştirmedik: **doğrulayamadığımız fiyatı hiç göstermiyoruz.** Bayat ya
da şüpheli bir fiyat, tahmin edilip gösterilmek yerine gizlenir. Fullet'in sana yanlış
istasyonu göstermemesi, çok istasyon göstermesinden daha önemli.

#### 🔎 Arama artık gerçekten "en yakın"ı gösteriyor

Yaygın markalarda (Shell, Opet, Petrol Ofisi) arama sonuçları, mesafeye göre
sıralanmadan önce kırpılıyordu. Sonuç: sana 2 km ötedeki istasyon, listede hiç
görünmeyebiliyordu — üstelik liste sıralı göründüğü için bunu fark etmen mümkün
değildi. Düzeltildi; artık listedeki 50 sonuç gerçekten en yakın 50 sonuç.

#### 📱 Android 16 uyumu ve arayüz iyileştirmeleri

- Android 16'nın yeni tam ekran (edge-to-edge) kurallarına tam uyum: istasyon detay
  paneli, yan menü ve harita düğmeleri sistem çubuklarının altında kalmıyor.
- Uzun sürüşlerde bellek kullanımı sabitlendi: harita ikonu önbelleği artık sınırlı.
- Çeşitli hata düzeltmeleri ve kararlılık iyileştirmeleri.

---

### 🔧 Teknik değişiklikler (kullanıcıya görünmeyen)

| Alan | Önce | Sonra |
|---|---|---|
| `minSdkVersion` | 21 (Android 5.0) | **24 (Android 7.0)** |
| `targetSdkVersion` | 35 | **36 (Android 16)** |
| Android Gradle Plugin | 8.2.1 | **8.11.1** |
| Gradle | 8.7 | **8.14** |
| Kotlin | 1.9.22 | **2.3.10** |
| NDK | 25.1.8937393 | **27.0.12077973** |
| Marker ikon önbelleği | sınırsız (bellek sızıntısı) | **300 girişli LRU** |
| Arama kırpması | sıralamadan önce (hatalı) | **sıralamadan sonra** |
| `flutter_lints` | ^2.0.0 | **^6.0.0** |
| `dart analyze` | 77 bulgu | **0 bulgu** |
| R8 küçültme / kaynak temizliği | kapalı | **açık** |
| Dart sembol gizleme | kapalı | **açık** (`--obfuscate`) |
| Async crash raporlama | yok | `PlatformDispatcher.onError` → Crashlytics |
| `google_maps_flutter` | 2.5.3 | **2.14.2** |
| Teşhis logları | `debugPrint` (release'de de yazıyordu) | `appLog()` → yalnızca debug |
| `android.enableJetifier` | true | kaldırıldı |

> ⚠️ **minSdkVersion 24:** Android 5.0 ve 5.1 çalıştıran cihazlar bu sürümden itibaren
> güncelleme alamaz. Bu karar bilinçli olarak verildi (4 Ağustos 2026).

---

### 📌 Yayın öncesi hatırlatma

Bu sürüm Play'e yüklenmeden önce `GOOGLE_PLAY_LAUNCH_CHECKLIST.md` içindeki bloklayan
işler tamamlanmalıdır — özellikle **upload keystore** ile imzalama.
