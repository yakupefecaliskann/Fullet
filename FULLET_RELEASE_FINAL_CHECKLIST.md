# FULLET — SON RELEASE CHECKLIST (Doğrulanmış Durum)

**Tarih:** 16 Haziran 2026
**Amaç:** Fullet'i production release'e hazır hale getirmek. Yeni özellik yok; sadece kritik riskleri kapatmak ve yayını açmak.
**Kanıt seviyeleri:** ✅ CONFIRMED (canlı/araçla doğrulandı) · 🔵 HAZIR (dosya/değer mevcut) · 👤 İNSAN (senin yapman gereken konsol işi)

Bu doküman, denetim raporundaki ([FULLET_RELEASE_DENETIMI.md](FULLET_RELEASE_DENETIMI.md)) 5 kritik işin (A1–A5) güncel durumudur.

---

## 1. ✅ Teknik tarafta doğrulananlar (bende biten işler)

| # | İş | Durum | Kanıt |
|---|---|---|---|
| A4 | Backend health check | ✅ Canlıda **exit 0** | 3423 istasyon, RLS aktif, RPC v1+v2 deploy, anon yazma engelli |
| A3 | pg_cron auto_price_staleness | ✅ **Canlı, aktif** | Job 1 (fresh→stale @12h) iş üstünde yakalandı; fresh max 4.3h, 49h+ stale yok |
| A4 | Canlı şema | ✅ Davranışsal doğrulandı | aktif/veri_kaynagi/provider kolonları + RLS + anon filtresi health check'te geçti |
| A5 | GitHub secrets + Actions | ✅ Ampirik doğrulandı | CI botları bugün canlıya yazdı (fresh veri <5h) → service_role secret + cron çalışıyor |
| A2 | Data Safety dokümanları | ✅ Gerçekle hizalandı | privacy.html, data-deletion.html, PLAY_STORE_READINESS, GOOGLE_PLAY_LAUNCH_CHECKLIST düzeltildi |
| — | Release imzalama | ✅ Güvenli | key.properties/keystore git'te DEĞİL; SHA-1 doğrulandı; sertifika 2053'e kadar |
| — | flutter analyze | ✅ Temiz | Kullanılmayan import kaldırıldı (station_bottom_sheet.dart) |
| — | flutter test + backend unit tests | ✅ Geçti | 17 backend test OK |
| — | Release AAB | ✅ Üretildi & imzalandı | `app-release.aab` 25.0 MB (16 Haz 17:22), release keystore ile imzalı |

---

## 2. 👤 Senin yapman gereken konsol işleri (kalanlar)

### A1 — Google Maps API key kısıtlama + bütçe (TEK GERÇEK MALİYET RİSKİ)

> **Önemli bağlam (denetimi yumuşatan bulgu):** Repo **private** ve admin panel/Pages Maps key içermiyor. Key sadece AndroidManifest.xml'de ve yayınlanan APK'dan zaten çıkarılabilir (her Android Maps key'i için kaçınılmaz). Yani **key'i rotate etmek ACİL DEĞİL** — gereken tek şey aşağıdaki kısıtlama. (İstersen yine de rotate edebilirsin, zararı yok.)

Google Cloud Console → APIs & Services → Credentials → Maps key (`AIzaSyC4Slx...8fLow`):

1. **Application restrictions → Android apps:**
   - Package name: `com.fullet.app`
   - SHA-1 (upload sertifikası): `40:9B:C1:14:68:F0:BC:0F:C1:58:BE:4B:56:5D:8D:FD:20:5E:96:89`
   - Play App Signing açıldıktan sonra Play Console'un verdiği **App signing SHA-1**'i de buraya ekle.
2. **API restrictions → Restrict key:** sadece **Maps SDK for Android** (kullanılan tek API).
3. **Bütçe + kota:** Cloud Console → Billing → Budgets & alerts → düşük bir bütçe + uyarı (örn. ₺0/aylık kullanım eşiği). Maps SDK kullanım kotasını da sınırla. "Sıfır maliyet" hedefi için sürpriz fatura kalmasın.

### A2 — Play Console Data Safety formu
Formu **[PLAY_STORE_READINESS.md](PLAY_STORE_READINESS.md) → "Data Safety Taslağı" tablosuna** göre doldur. Özet:
- Location (approx+precise), Personal info (Name+Email — yalnız Google ile giriş), App activity (interactions+search), App info & performance (crash+diagnostics), Device IDs.
- Data shared = No · Encrypted in transit = Yes · Data deletion = Yes → `https://yakupefecaliskann.github.io/Fullet/data-deletion.html`

### A5 — 30 saniyelik teyit (token olmadığı için ben listeleyemedim)
- Settings → Secrets and variables → Actions: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (veya service_role taşıyan `SUPABASE_KEY`), `SUPABASE_ANON_KEY` dolu mu?
- Actions sekmesi → son zamanlanmış run'lar **yeşil** mi? (Veri tazeliği zaten çalıştığını kanıtlıyor; bu sadece formalite.)
- İsteğe bağlı: SQL Editor'da `SELECT jobname, schedule, active FROM cron.job WHERE jobname LIKE 'fullet-%';` → 4 job `active=true`.

### A5b — pg_cron job listesini görmek istersen (opsiyonel)
Yukarıdaki SQL ile 4 job'ı gör. Kritik iki fiyat job'ı zaten canlı veriyle kanıtlandı; bu sadece tamlık içindir.

---

## 3. 👤 Play Store yükleme ve kapalı test

🔵 Hazır olanlar (repoda mevcut):
- Store görselleri: `play_store_assets/upload/` (telefon 6 + 7"/10" tablet) · feature graphic 1024×500 · 512 ikon.
- Privacy policy: `https://yakupefecaliskann.github.io/Fullet/privacy.html` (güncellendi, canlı).
- AAB: `fullet_flutter/build/app/outputs/bundle/release/app-release.aab` (sürüm 1.0.2+3).

👤 Yapılacaklar:
1. **Play App Signing** kurulumunu tamamla (AAB ilk yüklemede). Verilen App signing SHA-1'i A1'deki Maps key'e ekle.
2. **Internal testing** ile başla, sonra **Closed testing**.
3. Hesap 13 Kasım 2023'ten sonra açıldıysa: **12 tester × 14 gün kesintisiz opt-in** zorunlu — bu saati **bu hafta** başlat, yoksa production takvimi kayar.
4. Store listing metni (kısa + uzun açıklama, kategori, iletişim e-postası) gir. Açıklamada "fiyatlar resmi/marka kaynaklarından; tahmini fiyat gösterilmez" vurgusu olsun.
5. Production'a **kademeli rollout (%20→%50→%100)** ile çık; ilk crash dalgasını Crashlytics'te izle.

---

## 4. Bakımsız çalışma sınırı (dürüst not)

- **Tek gerçek sınır:** GitHub Actions zamanlanmış workflow'lar **60 gün** repo aktivitesi olmazsa otomatik devre dışı kalır. Gerçek hands-off tavanı **~2 ay**. Her ~8 haftada bir küçük bir commit (veya Actions'ı manuel "Enable") yeterli.
- Geri kalan her şey kendi kendine ayakta: fiyat botları (4×/gün), pg_cron bayatlatma (yanlış fiyat göstermez), CI dayanıklılığı (bir bot kırılsa diğerleri devam).

## 5. Bloklamayan operasyonel not
- Fiyat kapsamı şu an düşük: aktif fiyatların ~%91'i stale/unknown (fresh:590/7224). Uygulama unknown'ı gizler ve sadece fresh fiyata güvenir → **kullanıcıya yanlış fiyat gitmez**. Kapsamı artırmak (bot iyileştirme) yayını bloklamaz; release sonrası ele alınabilir.

---

### Sonuç
Teknik kritik işlerin tamamı (A2–A5 + build hijyeni) doğrulandı/düzeltildi. Yayını açmak için kalan **tek teknik dışı blok**, senin Google Cloud + Play Console konsol işlerin (A1 + Data Safety formu + kapalı test başlatma). Bunlar bitince **Fullet production release'e hazırdır.**
