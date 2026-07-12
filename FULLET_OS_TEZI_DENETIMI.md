# FULLET — "ARAÇ FİNANSAL İŞLETİM SİSTEMİ" TEZİ ALTINDA YENİDEN DENETİM

**Hazırlayan:** Bağımsız board / yatırım komitesi
**Tarih:** 16 Haziran 2026
**Konumlandırma:** Fullet = "en ucuz benzini bul" DEĞİL → **Türkiye'nin araç sahipleri için finansal işletim sistemi (Vehicle Financial OS)**, yakıt bunun yüksek-frekanslı kazanım kapısı.

> **Önce dürüst ol:** Bir pitch'i yeniden çerçevelemek gerçeği değiştirmez. Bu reframe **tavanı yükseltiyor, tabanı yükseltmiyor.** Vizyon yatırılabilir hale geliyor; ama yatırımcı vizyona değil, vizyona doğru olan **çekişe (traction)** para koyar. Bugün elinde bir yakıt haritası var, OS'in %0'ı inşa edilmiş değil. Aşağıda ikisini ayrı puanladım — birbirine karıştırmak dürüstsüzlük olur.

---

## ÜÇ SORUNUN KISA CEVABI

**1) Yatırılabilirlik puanı kaç olur?**
- **Tez/vizyon kalitesi: 58/100** — meşru bir playbook, büyük TAM, gerçek gelir. (Eskiden tüketici-yakıt tezi 22 idi.)
- **Fullet'in BUGÜNKÜ hali, bu vizyona doğru: 35/100** — tavan yükseldi, taban neredeyse sabit. Aradaki 23 puanlık fark = senin önündeki gerçek iş.

**2) Hangi özellikler kritik olur?**
Para motoru: **sigorta yenileme karşılaştırması + komisyon.** Retention motoru: **son-tarih hatırlatıcıları (MTV, muayene, sigorta, ruhsat).** Veri hendeği: **araç gider defteri / TCO paneli.** Kazanım kapısı: **yakıt + zam alarmı.** (Detay aşağıda.)

**3) Nasıl moat oluşur?**
Tek özellik değil, **dört katmanın birikimi:** (a) plaka-bazlı araç finansal veri grafiği, (b) takvim/hatırlatıcı bağımlılığı (switching cost), (c) banka ve e-Devlet'in vermediği **tarafsız toplayıcı** konumu, (d) lisans/broker ortaklığı + komisyon ekonomisi. (Detay aşağıda.)

---

## EN ÖNEMLİ TESPİT — REFRAME NEDEN GERÇEKTEN DAHA İYİ

Önceki raporda öldürücü tespit şuydu: Türkiye'de akaryakıt fiyat farkı yok, dolayısıyla "en ucuzu bul" değer önerisi çürük. **Bu reframe o sorunu çözmüyor — etrafından dolaşıyor, ki bu daha akıllıca.** Yakıt artık *ürün* değil; ucuz, yüksek-frekanslı, herkesin umursadığı bir **kazanım kanalı.** Asıl değer (ve para) araç sahibinin yılda defalarca yaşadığı gerçek finansal olaylarda: sigorta yenileme, MTV, muayene, ceza, HGS, 2. el değeri. Burada — yakıtın aksine — **gerçek fiyat dağılımı, gerçek son tarihler, gerçek ceza riski ve gerçek komisyon var.**

Bu, "fintech'in ücretsiz utility ile kullanıcı toplayıp komşu finansal ürünle para kazanması" playbook'unun ders kitabı versiyonu. Tez sağlam.

**Ama aynı anda bu, tamamen farklı ve çok daha zor bir şirket.** Daha fazla sermaye, lisans, domain uzmanlığı, ortaklık ve **çok daha güçlü rakipler** gerektiriyor. Yakıt haritası yapan tek kişilik bir ekip, buradan çok uzakta.

---

# A — ÜRÜN DENETİMİ (OS çerçevesi)

**Problem (yeni):** Araç sahibinin finansal hayatı dağınık ve cezalı. Sigorta ne zaman bitiyor, MTV son günü ne, muayene gecikti mi, kasko'da fazla mı ödüyorum, cezam var mı — hepsi ayrı silolarda (e-Devlet, banka app, sigorta acentesi, TÜVTÜRK). **Kimse bunları tek yerde, tarafsızca, proaktif olarak yönetmiyor.** Bu problem GERÇEK ve PARALI.

**İnsanlar öder mi? — Dolaylı olarak EVET.** Kullanıcı sana abonelik ödemez; ama sigortayı senin üzerinden yenilediğinde **sigorta şirketi komisyon öder.** Trafik+kasko Türkiye'de milyonlarca araç × anlamlı komisyon = gerçek gelir. Yakıttaki 9.9 TL ile kıyaslanamaz.

**30 saniye testi:** "Aracını ekle, tüm masraflarını ve son tarihlerini Fullet hatırlatsın + sigortanı karşılaştırıp en ucuzunu bulsun." Bu cümle anlaşılır VE umursanır. Eski cümle ("hepsi aynı fiyat") değildi.

**Mevcut varlıkların bu teze katkısı:** Temiz Flutter app + harita UX + "garaj/araç ekleme" altyapısı (artık gerçek anlam kazanıyor — araç profili OS'in temeli) + bot/veri toplama disiplini. Yani inşa ettiğin şeyin %20-30'u bu teze taşınabilir; gerisi yeni.

---

# B — PAZAR DENETİMİ

**Pazar büyüklüğü dramatik biçimde büyüdü.** Türkiye'de ~28-30M tescilli araç. Zorunlu trafik sigortası = her aracın yıllık tekrar eden olayı. Kasko penetrasyonu artıyor. MTV/muayene/ceza herkesi ilgilendiriyor. 2. el araç pazarı devasa. Bu, "fiyat farkı bul" niş pazarının 50 katı bir TAM.

**Trend mi kalıcı mı:** Kalıcı + dijitalleşen. Sigorta online satışı, e-Devlet entegrasyonları, banka super-app'leri hepsi bu yöne akıyor — yani trend senin lehine, ama **rakipler de aynı trende biniyor.**

**En iyi pazar artık Türkiye OLABİLİR** — çünkü değer fiyat-dağılımından değil, regülasyon yoğunluğundan (zorunlu sigorta, MTV, muayene, ceza) geliyor. Türkiye'nin "evrak/yükümlülük yoğun" araç sahipliği tam da bu OS'e zemin. İronik ama reframe coğrafya sorununu da düzeltiyor.

---

# C — RAKİP ANALİZİ (oyun tamamen değişti — ve zorlaştı)

| Rakip | Güçlü yanı | Zayıf yanı | Fullet'in açısı |
|---|---|---|---|
| **e-Devlet + SBM** | Ücretsiz, resmi, evrensel; cezalar, MTV, muayene, ruhsat ve **SBM sigorta teklifleri** zaten burada | Karşılaştırma/öneri/proaktiflik YOK, UX kötü, push yok | Tarafsız **zeka + takvim + karşılaştırma** katmanı — "erişim" değil "akıl" sat |
| **Koalay / Sigortam.net** | 35+ sigortacıyla karşılaştırma, lisans, marka, sermaye | Tek-amaçlı (sadece sigorta satışı), araç OS'i değil, retention'ı zayıf | Sigortayı daha geniş bir araç-yaşam bağlamına göm; sürekli ilişki |
| **Banka super-app'leri** (Garanti, İş, Akbank) | Ödeme + MTV/HGS/ceza + kendi sigortası + güven + para | Kendi ürününü iter (tarafsız değil), araç-merkezli değil | **Nötrlük:** "bankan sana kendi kaskosunu satar, biz en ucuzunu buluruz" |
| **GasAll / yakıt app'leri** | Yakıt tarafında kurulu taban | Sadece yakıt, OS değil | Yakıtı kapı olarak kullan, üstüne finansal katman koy |

### "Rakip olsaydım Fullet'i nasıl öldürürdüm?"
Bu sefer cevap eskisi gibi "hiçbir şey yapmam" değil — **pazar gerçek, o yüzden beni gerçekten öldürebilirsin.** Ama ben (örn. bir banka ya da Koalay) seni şöyle yavaşlatırım: (1) Koalay zaten lisanslı ve 35 sigortacıyla entegre — senin 12-18 ay süren entegrasyon+lisans yolunu onlar bugün geçmiş durumda; ben sadece bir "araç takvimi/hatırlatıcı" özelliği eklerim. (2) Banka, ödeme + güven elinde olduğu için MTV/HGS/ceza ödemesini app'inde tutar; senin için ödeme entegrasyonu ve güven inşası yıllar alır. (3) En tehlikelisi: **e-Devlet bedava ve resmi** — kullanıcının "neden ayrı app?" sorusuna her gün cevap vermek zorundasın.

---

# D — GELİR MODELİ (ARTIK GERÇEK BİR MODEL VAR)

- **Sigorta komisyonu (birincil motor):** Trafik + kasko yenilemede şirketten komisyon. Türkiye'de en kanıtlı dijital sigorta gelir modeli (Koalay bunun üstüne kuruldu). **Bu işin kalbi.**
- **Lead / yönlendirme:** Kredi (taşıt kredisi), 2. el satış/alış, lastik/bakım servisleri için CPA/lead.
- **Float/işlem:** HGS otomatik yükleme, ödeme akışları (banka ortaklığıyla).
- **Premium (ikincil):** Çoklu araç, gelişmiş TCO analizi, filo modu — KOBİ/küçük filo için aylık ücret *mantıklı hale gelir* (artık gerçek değer var).
- **B2B veri:** Anonim araç-gideri/talep verisi sigorta ve otomotiv için değerli.

**En iyi model:** **Komisyon-öncelikli + premium (KOBİ/filo) ikincil.** Reklam ve tüketici aboneliği unutulsun.

**Brutal uyarı:** Komisyon almak regüle. Şubat 2026'da SEDDK **yetkisiz online sigorta satışına** karşı sıkılaşıyor. Lisanssız saf "eşleştirme/lead" yasal ama gelir o oranda sınırlı; gerçek komisyon için **SEDDK acente/broker lisansı veya lisanslı bir broker ile white-label ortaklık** (ör. Koalay altyapısı üstüne) + sermaye gerekiyor. Bu, modelin hem motoru hem de en büyük kapısı.

---

# E — GROWTH (yakıt artık huninin başı, ürün değil)

- **İlk 100-1.000:** Yakıt haritası + **zam alarmı** ile ucuz kazanım — bu kanalın *amacı artık net.* Sonra araç ekleyene sigorta/son-tarih değeri sun.
- **İlk 10.000:** SEO ("MTV son ödeme tarihi", "muayene ne zaman", "trafik sigortası ne kadar") + zam günü içerik → yüksek niyetli trafik.
- **İlk 100.000:** Sigorta yenileme sezonu kampanyaları + "cezanı sorgula/hatırlat" viral utility + olası banka/sigortacı dağıtım ortaklığı.

**Kanal ROI (yeni tez):** 1) SEO (yükümlülük aramaları çok yüksek niyet) — **Yüksek.** 2) Yakıt+zam alarmı kazanım kapısı — **Orta-Yüksek.** 3) Sigorta/banka ortaklık dağıtımı — **Yüksek ama yavaş.** 4) Referral (gerçek tasarruf paylaşılabilir) — **Orta.** 5) Sosyal (artık "sigortada X TL kazandım" inandırıcı) — **Orta.**

---

# F — YATIRIMCI GÖRÜŞÜ

**1M$ olsa yatırır mıydım?** Vizyona **evet, koşullu**; bugünkü Fullet'e **henüz hayır.** Şunları görürsem pre-seed yazarım: (a) bir lisanslı broker/sigortacı ile imzalı entegrasyon ya da niyet, (b) sigorta/fintech domain'inden bir kurucu ortak, (c) yakıt huninin sigorta-niyetli kullanıcıya dönüştüğünü gösteren ilk veri.

**Riskler:** e-Devlet'in bedava+resmi olması; Koalay/Sigortam.net'in önde olması; SEDDK lisans/regülasyon yükü; cezalar/MTV/muayene için temiz yasal üçüncü-taraf API'sının olmaması (e-Devlet'i proxy'lemek riskli → OS'in büyük kısmı kullanıcı-girdisi+hatırlatıcıya dayanmak zorunda); solo kurucu; güven inşası; sermaye yoğunluğu.

**Fırsatlar:** Gerçek komisyon geliri; deadline-driven yüksek retention; biriken araç-finansal veri hendeği; tarafsız-toplayıcı boşluğu; KOBİ filo SaaS yukarı-satış.

**Yatırılabilirlik (bu vizyona doğru bugünkü Fullet): 35/100.** Tezin tavanı ~58. Aradaki fark, lisans + ortaklık + ekip + ilk traction ile kapanır.

---

# G — KURUCU ANALİZİ

Reframe **doğru içgüdü** — fikrin geliştiğini gösteriyor. Ama dikkat:
- **Kapsam riski:** "Araç finansal OS" cümlesi kolay, inşası bir yakıt haritasının 20 katı. Tek kişi bunu yürütemez. **En kritik aksiyon: sigorta/fintech kurucu ortağı.**
- **Regülasyon kör noktası:** Mühendis kafasıyla "entegre ederim" diyorsun; ama buradaki gerçek iş kod değil **lisans + ortaklık + güven.** Bunu küçümseme.
- **Veri illüzyonu:** e-Devlet verisini (ceza/MTV/muayene) yasal ve sürdürülebilir biçimde çekemezsin. OS'in o kısmını kullanıcı-girdisi + akıllı hatırlatıcı olarak tasarla; "resmi veriye erişim" üstüne moat kurma.
- **Sıralama riski:** Her şeyi aynı anda yapma. Tek bir kama seç (aşağıda).

---

# H — GERÇEKLİK TESTİ

- **Mevcut yakıt-tezi devam ederse batma: ~%88** (değişmedi).
- **OS-tezine başarıyla pivot ederse batma: ~%70, başarma ~%30.** Daha iyi ama hâlâ zor — çünkü rakipler güçlü, regülasyon ağır, sermaye gerek.

**En kritik 5 risk:** e-Devlet'in bedava+resmi rekabeti; sigorta lisans/regülasyon (SEDDK sıkılaşması); incumbent (Koalay/banka) önceliği; solo kurucu + sermaye; ceza/MTV verisine yasal erişim yokluğu.

**En kritik 5 karar:** (1) Lisanslı broker ortaklığı mı, kendi lisansın mı? (2) Kurucu ortak alacak mısın? (3) İlk kama hangisi (sigorta vs. hatırlatıcı)? (4) Tüketici komisyon mu, KOBİ filo SaaS mı önce? (5) Stop-loss: kaç ayda ilk imzalı sigorta ortaklığı + ilk komisyon geliri?

---

# I — YOL HARİTASI (OS tezine göre)

**30 gün — Kanıtla, kod yazma.** Yakıt app'ini yayınla (kazanım kapısı). Eş zamanlı: 30 araç sahibiyle konuş — "sigortanı son ne zaman, nasıl yeniledin, fazla mı ödedin?" Bir lisanslı broker (Koalay/Sigortam.net white-label ya da bir bağımsız acente) ile **ilk konuşmayı başlat.** Asıl soru: "Yakıt kullanıcısı sigorta-niyetli kullanıcıya dönüşür mü?"

**90 gün — İlk kama: Sigorta + Hatırlatıcı.** Tek bir şey inşa et: araç ekle → sigorta/MTV/muayene son tarihlerini hatırlat → sigorta yenilemede karşılaştırma (lisanslı ortak üstünden). Diğer her şey beklesin. İlk imzalı ortaklık + ilk lead/komisyon = yeşil ışık.

**6 ay — İlk gelir + retention kanıtı.** Ölç: hatırlatıcı kuran kullanıcının D30 retention'ı, sigorta lead → poliçe dönüşümü, araç başına komisyon. Bir kurucu ortak (domain) işe katılmış olmalı.

**1 yıl — Genişlet ama odaklı.** Sigorta motoru çalışıyorsa HGS/ceza utility + TCO paneli + 2. el değer ekle. KOBİ/filo premium pilotu. Gelir > altyapı.

**3 yıl — Gerçek "araç finansal OS"** ya da net pivot. Bu vizyon 3 yılda *mümkün* hale geliyor (eski tezde değildi) — ama yalnızca lisans + ortaklık + ekip + sermaye dizilirse.

---

# J — SON KARAR

## "Vizyona koşullu yatırım yaparım; bugünkü Fullet'e henüz yapmam."

OS reframe'i fikri yatırılabilir bandın kenarına taşıyor — ama yatırım, vizyon için değil, vizyona doğru ilk üç kanıt için gelir: **imzalı sigorta ortaklığı, domain kurucu ortağı, yakıt→sigorta dönüşüm verisi.**

| Kategori | Eski tez (yakıt) | OS tezi (bugünkü Fullet) | OS tezi (tavan/vizyon) |
|---|---:|---:|---:|
| **Genel** | 28 | **35** | **58** |
| Ürün (pazar-uyumu) | 18 | 40 | 65 |
| Growth | 25 | 42 | 60 |
| Pazar | 15 | 60 | 75 |
| Ekip (kapsam riski dahil) | 30 | 30 | 55 |
| Savunulabilirlik (moat) | 12 | 38 | 62 |
| Gelir modeli | 5 | 55 | 70 |

### Moat — nasıl oluşur (tek özellik değil, 4 katmanın birikimi)
1. **Veri grafiği:** plaka → marka/model/yıl + sigorta geçmişi + gider geçmişi + yakıt/sürüş deseni. Zamanla derinleşir; ne kadar uzun kullanır, o kadar zor terk eder.
2. **Takvim bağımlılığı:** MTV/muayene/sigorta/ruhsat tarihlerini bir kez Fullet'e öğrettiğinde, bunu başka yerde yeniden kurmak istemez. Ceza-önleme + zihinsel yük azaltma = güçlü switching cost.
3. **Tarafsız toplayıcı konumu:** Banka kendi ürününü satar, e-Devlet karşılaştırma/öneri sunmaz. "Senin tarafında olan tek akıl" boşluğu gerçek ve doldurulmamış.
4. **Komisyon/lisans ekonomisi:** Gerçek lead hacmine ulaşınca sigortacılardan tercihli oran; lisans/broker ortaklığı bir sonraki solo kurucu için de bariyer.

### "Fullet benim şirketim olsaydı yarın sabah ne yapardım?"
1. **Sabah:** Kod yazmazdım. **Bir lisanslı sigorta brokerine** (Koalay/Sigortam.net white-label veya bağımsız bir acente) e-posta atar, "araç sahibi kazanım kanalım var, sigorta lead/komisyon ortaklığı kurabilir miyiz?" toplantısı isterdim. Bu işin gerçek kilidi burada, kodda değil.
2. **Öğlen:** İlk kamayı **tek sayfaya** indirirdim: "Araç ekle → sigorta+MTV+muayene hatırlat → yenilemede karşılaştır." Cezalar/MTV'nin canlı resmi verisine güvenmeyen, kullanıcı-girdisi + hatırlatıcıya dayanan bir tasarım — e-Devlet'le savaşmadan onun yapmadığı şeyi yaparım.
3. **Öğleden sonra:** SEDDK lisans/yetkisiz-satış kurallarını okur, "lisanssız ne yapabilirim (matching/lead), komisyon için kiminle ortak olmalıyım" sınırını netleştirirdim. Regülasyonu sonradan değil, başta çözerim.
4. **Akşam:** Bir **kurucu ortak** arardım — sigorta/fintech domain'inden. Çünkü bu şirket benim tek başıma (yakıt haritası yapan mühendis olarak) yürütebileceğim bir şirket değil; bunu kabul etmek en değerli kararım olurdu.

### Kapanış
Reframe doğru ve fikri ciddiye alınır hale getiriyor — tebrik değil, tespit. Ama unutma: **vizyon bedava, traction pahalı.** Yakıt artık akıllı bir kapı; arkasındaki odayı (sigorta komisyonu + takvim retention'ı + veri hendeği) gerçekten inşa edersen burada bir şirket var. İnşa etmezsen, bu sadece daha iyi yazılmış bir slayt olur. Beni 90 günde imzalı bir sigorta ortaklığı ve ilk komisyon geliriyle çürüt — o zaman 35'i 50'ye çıkarır, çek yazarım.

*— Bağımsız board / yatırım komitesi*
