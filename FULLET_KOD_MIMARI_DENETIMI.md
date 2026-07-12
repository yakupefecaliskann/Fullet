# FULLET — UÇTAN UCA KOD, MİMARİ VE UX DENETİMİ

**Rol:** Teknik denetçi (mevcut kodu kırılganlık/performans/güvenlik açısından tarayan CTO bakışı)
**Tarih:** 8 Temmuz 2026
**Kapsam:** `scraper/` (10 bot + orkestrasyon + DB yazma katmanı), `fullet_flutter/lib/` (state, servisler, ekranlar, widget'lar), `supabase/` (edge functions, migrations), `database/` (RLS, hardening, cron), `admin_panel/`.
**Yöntem:** Kod tam okuma + üç paralel derin analiz (bot mimarisi, Flutter performansı, Supabase güvenliği) + **canlı Supabase projesine (`xhkvlwecsacfjpbtyqcc`) doğrudan sorgu ile doğrulama** (RLS durumu, uygulanan migration'lar, security advisor çıktısı).

> **Tek cümlelik sonuç:** Botların hata toleransı (retry/timeout/telemetri) ve fiyat doğrulama katmanı beklenenden olgun; asıl risk **"sessiz yarı-başarı"** senaryolarında — bot az veri döndürdüğünde bunun "site değişti" mi "gerçekten güncelleme yok" mu olduğunu sistem ayırt edemiyor ve en az bir yerde (`_reset_split_region_targets`) bu durum aktif istasyonları yanlışlıkla gizleyebiliyor. UI tarafında en büyük jank kaynağı tek bir `context.watch` + tek bir `BackdropFilter`. Canlı DB'de RLS iddia edilenle gerçek durum arasında **iki yerde** fark var (biri düzeltilmiş ama iz bırakılmamış, biri hâlâ açık).

---

## KRİTİK — Bu hafta kapatılmalı

### K1. Bölgesel (split-region) kısmi kazıma, tüm şehirdeki istasyonları yanlışlıkla gizleyebiliyor
**Dosya:** `scraper/database_writes.py:209-225` (`_reset_split_region_targets`)

Şu an İstanbul için "regional_official" fiyat verisi geldiğinde, fonksiyon **önce** o marka+şehirdeki TÜM istasyonları `aktif=False` yapıyor, sonra bu run'da gelen (marka, ilçe) çiftlerine göre yeniden aktif ediyor. Sorun: kazıma bu run'da İstanbul'un sadece bir kısmını (örn. site zaman aşımına uğradığı için 20 ilçeden 8'ini) döndürürse, geri kalan 12 ilçedeki gerçek/güncel istasyonlar **kalıcı olarak gizlenmiş** kalıyor — bir sonraki başarılı run'a kadar. Bu, "kısmi veri → sessizce no-op" beklentisinin tam tersi; kısmi veri aktif olarak veri kaybına dönüşüyor.

```python
# scraper/database_writes.py — MEVCUT (riskli)
def _reset_split_region_targets(items: list[dict[str, Any]]) -> None:
    assert supabase is not None
    reset_groups = {
        (item["marka"], item["il"])
        for item in items
        if item.get("veri_kapsami") == "regional_official"
        and item.get("il") == "ISTANBUL"
        and item.get("ilce") in ISTANBUL_REGION_DISTRICTS
    }
    for brand, city in sorted(reset_groups):
        supabase.table("istasyonlar").update({
            "aktif": False,
            "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
        }).eq("marka", brand).eq("il", city).not_.ilike(
            "isim", "%Fullet Verisi%"
        ).execute()
        print(f"[INFO] Reset {brand} {city} before split-region price write.")
```

**Düzeltme:** reset işlemini, sadece bu run **tüm beklenen ilçeleri** kapsadıysa çalıştır. Kapsam eksikse hiçbir şeyi gizleme; mevcut zero-cost diff + staleness pipeline (`price_status`) zaten eskiyen veriyi doğal yoldan `stale`/`unknown`'a çeker.

```python
def _reset_split_region_targets(items: list[dict[str, Any]]) -> None:
    assert supabase is not None
    reset_groups: dict[tuple[str, str], set[str]] = {}
    for item in items:
        if (
            item.get("veri_kapsami") == "regional_official"
            and item.get("il") == "ISTANBUL"
            and item.get("ilce") in ISTANBUL_REGION_DISTRICTS
        ):
            reset_groups.setdefault((item["marka"], item["il"]), set()).add(item["ilce"])

    expected_districts = (
        set(ISTANBUL_REGION_DISTRICTS["ANADOLU"]) | set(ISTANBUL_REGION_DISTRICTS["AVRUPA"])
    )

    for (brand, city), seen_districts in sorted(reset_groups.items()):
        if seen_districts != expected_districts:
            missing = sorted(expected_districts - seen_districts)
            print(
                f"[WARN] {brand} {city} split-region kazıma eksik "
                f"({len(seen_districts)}/{len(expected_districts)} ilçe, eksik: {missing}) "
                f"— toplu gizleme ATLANDI (yarım veriyle istasyon gizlemek daha riskli)."
            )
            continue
        supabase.table("istasyonlar").update({
            "aktif": False,
            "guncellenme_tarihi": datetime.now(timezone.utc).isoformat(),
        }).eq("marka", brand).eq("il", city).not_.ilike(
            "isim", "%Fullet Verisi%"
        ).execute()
        print(f"[INFO] Reset {brand} {city} (tam kapsam doğrulandı).")
```

---

### K2. Fiyat botlarının hiçbirinde HTTP retry/backoff yok
**Dosyalar:** `opet_bot.py`, `aytemiz_bot.py`, `bp_bot.py`, `po_bot.py`, `total_bot.py`, `tp_bot.py`, `tp_station_bot.py`, `total_station_bot.py` — hepsi tek seferlik `requests.get(...)`.

Tek istisna `shell_station_bot.py` (3 denemeli manuel retry var — desenin bilindiğini ama uygulanmadığını gösteriyor). `run_all_bots.py` seviyesinde bot-script bazlı 1 ek deneme var (20s backoff), ama bu **tüm scripti** yeniden çalıştırıyor — tek bir HTTP isteğindeki geçici bir 502/timeout, o markanın **tüm günün o çalıştırmasını** feda ediyor demek.

**Düzeltme:** Paylaşılan, retry'lı bir `requests.Session` — tek yerde tanımla, tüm price botlarında kullan.

```python
# scraper/http_utils.py  (YENİ dosya)
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(total_retries: int = 3, backoff_factor: float = 1.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0 (Fullet fuel price monitor)"})
    return session


HTTP = build_session()
```

```python
# scraper/opet_bot.py — ÖNCESİ
response = requests.get(url, headers=HEADERS, timeout=20)
response.raise_for_status()

# SONRASI
from http_utils import HTTP
response = HTTP.get(url, timeout=(5, 20))  # (connect, read) — bağlantı takılırsa 5s'de anla
response.raise_for_status()
```

Aynı değişikliği `aytemiz_bot.py`, `bp_bot.py`, `po_bot.py`, `total_bot.py._get_json`, `tp_bot.py`, `tp_station_bot.py`, `total_station_bot.py._get_json` içindeki her `requests.get` çağrısına uygula (tümü `import requests` yerine `from http_utils import HTTP` kullanacak şekilde).

---

### K3. Pozisyonel/DOM-index tabanlı parsing, site yapısı değiştiğinde sessizce yanlış veri üretiyor
**Dosyalar:** `shell_bot.py:120-129` (`_prices_from_row`, `cols[4]`/`cols[12]` gibi sabit indeksler), `bp_bot.py:44-48` & `po_bot.py:44-48` (aynı desen), `aytemiz_bot.py:15-33` (token-stream heuristiği, `price_start = 6`).

Kaynak site bir kolon ekler/çıkarırsa iki senaryodan biri olur: (a) uzunluk kontrolü tüm satırları atlar → o markadan **0 fiyat** gelir ama bu "site kapalı" ile aynı görünür, ayırt edilemez; (b) daha kötüsü, uzunluk kontrolünü geçer ama yanlış kolonu okur → **plausible ama yanlış fiyat** DB'ye yazılır (örn. Motorin fiyatı Kursunsuz 95 diye kaydedilir), çünkü `parse_price`'ın 0-300 TL sınırı bunu yakalamaz.

**Düzeltme:** Her botun beklenen minimum satır sayısını tanımla; bu eşiğin çok altına düşen bir çalıştırmayı "başarılı ama boş" değil, **"muhtemelen site değişti"** olarak işaretleyip reddet — mevcut `run_all_bots.py` retry/alert altyapısını (K2'de bahsedilen) tetiklemesi için exit code != 0 döndür.

```python
# scraper/opet_bot.py (ve diğer price bot'lar) — __main__ bloğuna ekle
EXPECTED_MIN_ROWS = 400  # son 30 günün ortalamasının ~%30'u — ops_report.py'deki
                          # MIN_ACTIVE_STATIONS ile aynı mantık, burada "erken" uygulanıyor

if __name__ == "__main__":
    start_time = datetime.now()
    data = scrape_opet_data()
    if 0 < len(data) < EXPECTED_MIN_ROWS * 0.3:
        print(
            f"[FAIL] Opet kazıma sadece {len(data)} satır döndürdü "
            f"(beklenen ~{EXPECTED_MIN_ROWS}). Muhtemel site yapı değişikliği — "
            f"yanlış/eksik veriyi normal güncelleme gibi göstermemek için YAZMA reddedildi."
        )
        raise SystemExit(1)
    save_to_supabase(data, default_brand="Opet")
    print(f"[OK] Opet finished in {(datetime.now() - start_time).total_seconds():.1f}s.")
```

Bu, mevcut `TOLERATED_FAILURE_BOTS` / `create_system_alert` mekanizmasını **olduğu gibi** kullanır — yeni bir alarm sistemi icat etmeye gerek yok, sadece "az veri" durumunu "hata" olarak sinyallemek yeterli.

---

### K4. `BackdropFilter` blur — en sık kullanılan etkileşimde (istasyon dokunma) ana jank kaynağı
**Dosya:** `fullet_flutter/lib/widgets/station_bottom_sheet.dart:180-181`

```dart
// MEVCUT
BackdropFilter(
  filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
  child: Container(...),
)
```

`BackdropFilter`, altındaki her frame'de canlı `GoogleMap`'i de içeren bir `saveLayer` + GPU blur pass zorluyor. Bu sheet her istasyon dokunuşunda açılıyor, sürükle-genişlet animasyonu var, ve `ModernMapScreen`'in geniş `context.watch` rebuild kapsamı (K5) açıkken de yeniden çiziliyor — orta seviye Android cihazlarda gözle görülür kasma riski en yüksek nokta burası.

**Düzeltme:** Canlı blur yerine yarı saydam katı renk (görsel olarak neredeyse ayırt edilemez, maliyeti sıfıra yakın) + `RepaintBoundary` ile map'ten izolasyon:

```dart
// SONRASI
RepaintBoundary(
  child: Container(
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surface.withOpacity(0.94),
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
    ),
    child: ...,
  ),
)
```

Blur görünümü ürün açısından şart ise: sigma'yı 20'den 8-10'a düşür (maliyet sigma ile ölçekleniyor) **ve** sadece sheet tam açılıp sabitlendiğinde (`AnimationStatus.completed`) uygula, sürükleme sırasında düz renge düş.

---

### K5. `context.watch<UserPreferencesProvider>()` — ana ekranın tamamını gereksiz yere rebuild ediyor
**Dosya:** `fullet_flutter/lib/screens/modern_map_screen.dart:1523`

`UserPreferencesProvider` tek, monolitik bir `ChangeNotifier` (tank kapasitesi, yakıt tüketimi, seçili yakıt, favoriler, son ziyaret edilenler, araç — hepsi bir arada). Bu satır yüzünden **herhangi biri** değiştiğinde (`rememberStation()` her istasyon dokunuşunda çağrılıyor — `modern_map_screen.dart:1389`) `TopSearchBar`, marka filtre listesi, durum/sürüş banner'ları, FAB yığını, yan menü, alt sheet — haritanın kendisi hariç (o `ValueListenableBuilder` ile doğru izole edilmiş) **her şey** yeniden inşa ediliyor. Grep sonucu: projede hiçbir yerde `Selector`/`context.select` kullanılmıyor.

**Düzeltme:** İhtiyaç duyulan alanı `context.select` ile daralt; geniş `prefs` ihtiyacı olan alt ağaçları kendi `Selector`'larına taşı.

```dart
// ÖNCESİ
final prefs = context.watch<UserPreferencesProvider>();
// ... build() boyunca prefs.selectedFuel, prefs.favoriteStationIds, prefs.vehicle vs. karışık kullanılıyor

// SONRASI — bu build() kapsamında gerçekten okunan tek alanı seç
final selectedFuel = context.select<UserPreferencesProvider, String>(
  (p) => p.selectedFuel,
);

// Favori/araç bilgisine ihtiyaç duyan alt widget'ları kendi Selector'ına sar:
Selector<UserPreferencesProvider, Set<String>>(
  selector: (_, p) => p.favoriteStationIds,
  builder: (context, favoriteIds, _) => FulSideMenu(favoriteIds: favoriteIds),
)
```

Orta vadede: `UserPreferencesProvider`'ı `FavoritesProvider` / `VehicleProvider` / `FuelSelectionProvider` gibi ayrı `ChangeNotifier`'lara bölmek bu sınıfta yapısal olarak tekrar oluşacak sorunları kökten çözer — tek provider'da kaldığı sürece `Selector` sadece semptomu hafifletir.

---

### K6. Kalıcı önbellek yok — her soğuk açılış ağa bloklanıyor
**Dosya:** `fullet_flutter/lib/screens/modern_map_screen.dart:121-131` (`_initData`), `lib/services/supabase_service.dart:11-16` (sadece 5 dakikalık **bellek-içi** cache, uygulama yeniden başlayınca sıfırlanıyor)

Ana harita ekranı `_getLocation()` → `_fetchStationsForRegion()` bitene kadar tam ekran `CircularProgressIndicator` gösteriyor; kötü bağlantıda kullanıcı boş harita görüyor. "Önce bilinen son veriyi göster, arka planda tazele" deseni hiç yok — tam olarak sizin sorduğunuz "botların gereksiz çalışmasını engelleyecek / açılış hızını artıracak cache" ihtiyacı burada karşılanmıyor.

**Düzeltme:** Hive tabanlı kalıcı istasyon cache'i, soğuk açılışta anında göster, arka planda tazele.

```dart
// lib/services/station_cache_service.dart (YENİ dosya)
class StationCacheService {
  static const _boxName = 'station_cache_v1';
  static const _key = 'last_stations';

  Future<List<Station>> loadCached() async {
    final box = await Hive.openBox(_boxName);
    final raw = box.get(_key) as String?;
    if (raw == null) return [];
    final list = jsonDecode(raw) as List;
    return list.map((e) => Station.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> save(List<Station> stations) async {
    final box = await Hive.openBox(_boxName);
    await box.put(_key, jsonEncode(stations.map((s) => s.toJson()).toList()));
  }
}
```

```dart
// modern_map_screen.dart — _initData() içine
Future<void> _initData() async {
  final cached = await _stationCache.loadCached();
  if (cached.isNotEmpty && mounted) {
    setState(() {
      _stations = cached;
      _isLoading = false; // eski veriyi hemen göster, boş ekran yok
    });
    _updateCalculationsAndMarkers();
  }
  await _getLocation();
  await _fetchStationsForRegion(...); // tamamlanınca _stationCache.save(...) çağır
}
```

`Station` modelinde `toJson()` yoksa eklenmesi gerekir (mevcut `fromJson` zaten var).

---

### K7. pg_cron bayatlama job'larının başarısızlığı hiçbir yere düşmüyor
**Dosya:** `database/auto_price_staleness.sql` — fresh→stale (12s), stale→unknown (48s), visible→low_priority (7g), token temizliği

Python bot tarafında `telemetry.py` iki ardışık hatada Discord'a + `system_alerts`'e alarm basıyor; ama DB tarafındaki bu 4 cron job için **hiçbir hata yakalama/alarm yok**. Bir job sessizce durursa (izin değişikliği, fonksiyon hatası vb.) fark etmenin tek yolu Supabase panelinde `cron.job_run_details`'i elle sorgulamak — yani "eski fiyat gösterme" güvenlik ağının kendisi izlenmiyor.

**Düzeltme:** Job gövdesini bir fonksiyona alıp exception'ı `system_alerts`'e yaz (mevcut bot alarm deseniyle aynı tablo):

```sql
create or replace function public.fn_mark_stale_prices()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.fiyatlar
  set price_status = 'stale'
  where price_status = 'fresh'
    and son_guncelleme < now() - interval '12 hours';
exception when others then
  insert into public.system_alerts (severity, source, title, message, metadata)
  values (
    'error',
    'pg_cron:fn_mark_stale_prices',
    'Bayatlama cron job''ı hata verdi',
    sqlerrm,
    jsonb_build_object('sqlstate', sqlstate)
  );
  raise;
end;
$$;

select cron.schedule('fullet-mark-stale', '*/15 * * * *', $$select public.fn_mark_stale_prices();$$);
```

Aynı sarmalayıcıyı diğer 3 job'a da (stale→unknown, visibility düşürme, token temizliği) uygula.

---

### K8. Canlı DB'de doğrulanan iki gerçek RLS farkı

Bu denetim sırasında `mcp__Supabase` ile canlı projeye (`xhkvlwecsacfjpbtyqcc`) doğrudan sorgu attım. Sonuç:

- **İyi haber:** `fullet_users`, `fullet_favorites`, `price_alerts` tablolarının RLS'i **açık ve doğru** — `authenticated` rolüne, sadece `firebase_uid = auth.jwt()->>'sub'` eşleşen satırlar için `FOR ALL` politikası tanımlı. (`supabase/migrations/20260708120000_users_favorites_rls.sql`'de belgelenen "RLS'siz, anon tam CRUD açık" riski **canlıda artık yok**, doğrulandı.)
- **Kötü haber:** `mcp__Supabase__list_migrations` canlı projede **tek bir migration** gösteriyor (`20260708090025_nearby_stations_brand_filter`) — yukarıdaki RLS düzeltmesi dahil, `BACKEND_RUNBOOK.md`'de sıralanan onlarca SQL dosyası Supabase'in migration geçmişinde **hiç görünmüyor**. Bunlar SQL Editor'den elle çalıştırılmış, yani "hangi dosya canlıya gerçekten uygulandı" sorusunun tek kaynağı şu an kimsenin takip etmediği bir insan hafızası. `database/production_hardening.sql`'in kendi başlığı "PROD'da tekrar çalıştırma" uyarısı taşırken `BACKEND_RUNBOOK.md` onu adım 1 olarak listeliyor — bu çelişki `database/README.md`'ye göre **geçmişte bir kez gerçekten sorun yaratmış**.
- **Ayrıca canlıda doğrulanan, düzeltilmemiş bir bulgu:** Security Advisor'a göre `public.spatial_ref_sys` tablosunda RLS **hâlâ kapalı** (`rls_disabled_in_public`, ERROR seviye) — `database/postgis_spatial_ref_sys_rls.sql` dosyası repoda var ama canlıya hiç uygulanmamış görünüyor. Aynı "dosya var ama uygulandığı belirsiz" problemi burada da somut olarak yakalandı.

**Düzeltme (süreç):** SQL Editor'den elle çalıştırma alışkanlığını bırakmak büyük bir değişiklik gerektirir; asgari çözüm, her betiğin sonuna kendini kaydeden bir defter eklemek:

```sql
create table if not exists public._manual_migrations_log (
  id bigserial primary key,
  filename text not null unique,
  applied_at timestamptz not null default now()
);

-- her database/*.sql dosyasının EN SONUNA ekle:
insert into public._manual_migrations_log (filename)
values ('20260708120000_users_favorites_rls.sql')
on conflict (filename) do nothing;
```

**Düzeltme (spatial_ref_sys — hemen uygulanabilir):**

```sql
alter table public.spatial_ref_sys enable row level security;
revoke all on public.spatial_ref_sys from anon, authenticated;
```

---

## YÜKSEK — Bu sprint içinde planlanmalı

| # | Konu | Dosya | Risk | Kısa çözüm |
|---|---|---|---|---|
| Y1 | `shell_bot.py`/`shell_station_bot.py` `TOLERATED_FAILURE_BOTS` listesinde — en büyük marka (Shell, `ops_report.py`'de eşik 500 istasyon) kalıcı kırılsa bile pipeline hiç kırmızı olmaz, sadece "info" alarm | `run_all_bots.py:42-45` | Shell'in DOM tabanlı kazıması (K3) bozulursa haftalarca fark edilmeyebilir | Info alarmını Discord'a da düşür (şu an sadece `system_alerts`'e yazılıyor, `telemetry.py`'nin consecutive-failure eşiği sadece "error" severity'yi sayıyor — "tolerated" olsa bile 3+ ardışık başarısızlıkta escalate et) |
| Y2 | İstasyon envanteri yazımında (`_bulk_write_station_inventory`) update/insert `.execute()` çağrıları try/except'siz; batch 3/5 patlarsa 1-2 yazılmış olsa da tüm çağrı "skipped" olarak raporlanır | `database_writes.py:179-182` | Kısmi yazım + yanlış özet raporu — operasyonel körlük | Her batch'i kendi try/except'ine al, kısmi başarıyı da say/raporla |
| Y3 | `marker_icon_factory.dart`'taki statik `BitmapDescriptor` cache'i hiç sınırlanmıyor/temizlenmiyor | `lib/utils/marker_icon_factory.dart:7` | Uzun oturumlarda yavaş bellek sızıntısı | LRU sınırı ekle (örn. `LinkedHashMap` + 200 girişte en eskiyi at) |
| Y4 | `main.dart`'ta `dotenv.load` ve `Supabase.initialize` try/catch'siz — Firebase init'in hemen yanında ama korumasız | `lib/main.dart:40, 52-62` | `.env` paketleme sorununda uygulama `runApp()`'a hiç ulaşmadan çöküyor, kullanıcıya hiçbir mesaj yok | Firebase init'teki gibi try/catch + `_ConfigurationErrorApp` fallback'ine düşür |
| Y5 | Fiyat sınırı iki yerde farklı: parse-time `0 < x < 300` (`normalization.py:88,111`) vs health-check `5 <= x < 200` (`backend_health_check.py:229-231`); ayrıca legacy migration (`20260505195000_production_hardening.sql:200-201`) hâlâ `0 < x < 300` CHECK'i taşıyor | `normalization.py`, `backend_health_check.py`, eski migration | Health-check kendi kabul ettiği veriyi "geçersiz" diye işaretleyebilir; K8'deki gibi legacy dosya yanlışlıkla tekrar çalışırsa DB kısıtı sessizce gevşer | Tüm sınırları `5 <= x < 200`'e hizala; legacy migration dosyasına "ÇALIŞTIRMA" başlığı ekle (production_hardening.sql'deki gibi) |
| Y6 | Arama sheet'inde filtre/sıralama (`_searchResults`, `_priceSortedResults`) her `build()`'de yeniden hesaplanıyor, `_filteredStations` de aynı şekilde `build()` içinde tekrar çağrılıyor (zaten `_updateCalculationsAndMarkers()`'da hesaplanmışken) | `modern_map_screen.dart:1714, 2432-2533` | İstasyon sayısı büyüdükçe her tuş vuruşunda O(n) yeniden hesap | Sonucu `_query`/veri değişimine bağlı bir alan olarak cache'le, `build()` içinde sadece oku |
| Y7 | Scraper botlarında ciddi kod tekrarı: `PROVINCES` seti `shell_bot.py` ve `shell_station_bot.py`'de birebir kopya; `_first_price` regex helper'ı `bp_bot.py`/`po_bot.py`'de birebir kopya; `_get_json` deseni `total_bot.py`/`total_station_bot.py`'de birebir kopya | çoklu dosya | Bir kopyada yapılan düzeltme diğerine yansımıyor, sessiz davranış farkı riski | Ortak yardımcıları `normalization.py`/yeni `http_utils.py`'a taşı |

---

## ORTA — Planlanmalı, acil değil

| # | Konu | Dosya | Not |
|---|---|---|---|
| O1 | `push_tokens` tablosuna anon rolü hiçbir sahiplik/rate-limit kontrolü olmadan `INSERT` yapabiliyor | `database/rls_policies.sql:79-85` | Sadece uzunluk/provider CHECK var; kötü niyetli doldurma `fiyat-push`'ın boşa Expo çağrısı yapmasına yol açar. Basit bir IP/tarihe göre rate-limit trigger'ı eklenebilir |
| O2 | `fiyat-push` ve `set-authenticated-role` edge function'ları ham hata metnini (`error.message`, Google API response body) çağırana döndürüyor | `supabase/functions/fiyat-push/index.ts:78-80,106-108`, `set-authenticated-role/index.ts:204-208` | `fiyat-push` sadece service-role ile erişilebilir (düşük risk); `set-authenticated-role` herhangi bir Firebase kullanıcısına açık — jenerik hata mesajına geç, detayı sadece log'a yaz |
| O3 | `get_nearby_stations_v2` her istasyon satırı için korele alt sorgu ile fiyat JSON'u topluyor (`jsonb_object_agg` per-row) | `database/create_postgis_rpc.sql:102-113` | `max_results` üst sınırı 1000'de ölçülebilir maliyet; tek `LEFT JOIN` + `jsonb_object_agg` ile set-tabanlı birleştirmeye çevrilebilir |
| O4 | `istasyonlar.marka` kolonunda CHECK kısıtı yok, whitelisting sadece Python tarafında (`config.py:VALID_BRANDS`) | DB şeması | Doğrudan DB yazımı/gelecekteki bug ile çöp marka değeri sessizce dashboard'da görünmez hale gelebilir | `CHECK (marka = ANY(ARRAY['Shell','Opet',...]))` ekle |
| O5 | Security Advisor: 4 fonksiyonda `search_path` sabitlenmemiş | canlı DB | Aşağıdaki SQL ile tek seferde kapatılabilir (gerçek imzalar canlıdan doğrulandı) |
| O6 | `MediaQuery.of(context)` kullanımı yaygın, `MediaQuery.sizeOf(context)`/`.paddingOf(context)` yerine | `garage_modal.dart:364,421`, `station_bottom_sheet.dart:584,593` vb. | Klavye açılışı gibi ilgisiz `MediaQueryData` değişikliklerinde de gereksiz rebuild — düşük ama yaygın |
| O7 | `_bulk_upsert_prices`'ta mevcut fiyat fetch'i batch bazında başarısız olursa o batch "hiç yok" sayılıp zorla `fresh` olarak üzerine yazılıyor | `database_writes.py:33-44` | Veri kaybı değil ama gereksiz "fiyat değişti" sinyali üretebilir | Fetch başarısız olan station_id'leri upsert listesinden çıkar, bir sonraki run'a bırak |
| O8 | Hata tespiti string-matching ile yapılıyor: `"veri_kaynagi" not in str(exc)` (`database_writes.py:97`), `"system_alerts" in text` (`telemetry.py:16-24`) | scraper | Supabase/PostgREST hata metni değişirse bu kırılgan kontroller sessizce yanlış davranır | PostgREST hata kodlarını (`PGRST205` vb.) `exc.code`/`exc.details` gibi yapılandırılmış alandan oku, string içinde arama |

```sql
-- O5 çözümü (gerçek imzalar canlı projeden doğrulandı)
alter function public.log_fiyat_degisimi() set search_path = public;
alter function public.set_istasyon_konum() set search_path = public;
alter function public.get_nearby_stations(
  lat double precision, lng double precision, max_dist_meters integer,
  max_results integer, brand_filter text[]
) set search_path = public;
alter function public.get_nearby_stations_v2(
  lat double precision, lng double precision, max_dist_meters integer, max_results integer
) set search_path = public;
```

---

## DÜŞÜK — Teknik borç / temizlik

- `fullet_flutter/.env`, `pubspec.yaml:40`'ta Flutter **asset** olarak paketleniyor — APK/IPA açılınca ham dosya çıkarılabilir. Şu an içinde sadece public anon key var (risk yok) ama ileride gerçek bir gizli anahtar oraya eklenirse tehlikeli bir alışkanlık. `--dart-define-from-file` ile build-time enjeksiyona geçilmeli.
- `ListView.builder`/`.separated` öğelerine `key:` verilmiyor (`ful_side_menu.dart:1366`, `garage_modal.dart:378,438`) — bugün sorun yaratmıyor, liste yeniden sıralanmaya başlarsa (örn. favoriler sürükle-bırak) state karışabilir.
- Çok sayıda yerde eksik `const` constructor (`modern_map_screen.dart`, `station_bottom_sheet.dart`, `ful_side_menu.dart`) — K5 ile birlikte rebuild maliyetini büyütüyor.
- `marker_icon_factory.dart:39-40`'ta `BitmapDescriptor.fromBytes` deprecated API, `// ignore` ile susturulmuş.
- `pubspec.yaml:32` — `flutter_lints: ^2.0.0` güncel majör sürümlerin gerisinde, yeni performans/deprecation lint kuralları devre dışı.
- `scraper/requirements.txt` (Aralık 2023 / Ocak 2024 sabit sürümler) için transitive bağımlılık lockfile'ı yok (`pip-compile`/`poetry.lock`).
- Scraper test kapsamı ince: ~4100 satır üretim koduna karşı 3 test dosyası (~360 satır); `opet_bot.py`, `bp_bot.py`, `po_bot.py`, `total_bot.py`, `tp_bot.py`, `tp_station_bot.py`, `total_station_bot.py`, `shell_station_bot.py` için hiç test yok.
- `fiyat-push` fonksiyonu ismine rağmen fiyat değil sadece özet bildirimi gönderiyor — isim yanıltıcı, gerçek fiyat yazımı Python tarafından service-role ile doğrudan yapılıyor.
- Discord webhook hatası ve `summary_push` hatası sessizce yutuluyor (`telemetry.py:123-126`, `database_writes.py:276-277`) — tek dış kanalın kendisi bozulursa fark edilmiyor (dead-man's-switch yok).
- Security Advisor: "Leaked Password Protection Disabled" — Supabase Dashboard → Authentication → Policies'den tek tıkla açılabilir, kod değişikliği gerekmiyor.
- `is_fullet_admin()` fonksiyonu `anon` rolüne de EXECUTE izni veriyor (SECURITY DEFINER) — pratikte zararsız (auth.email() anon için null, false döner) ama gereksiz yüzey: `revoke execute on function public.is_fullet_admin() from anon;`

---

## Önceliklendirme özeti

1. **K1** (istasyon gizleme bug'ı) ve **K8'in spatial_ref_sys kısmı** — kod/SQL değişikliği küçük, etkisi büyük, bugün uygulanabilir.
2. **K2 + K3** birlikte — bot dayanıklılığının asıl iskeleti; `http_utils.py` eklemek tüm price botlarını aynı anda güçlendiriyor.
3. **K4 + K5** birlikte — ikisi de `ModernMapScreen`'de, ikisi de en sık kullanılan etkileşimi (istasyon dokunma) etkiliyor; aynı PR'da ele alınabilir.
4. **K6** — kullanıcı deneyimine en görünür etkisi olan madde, ama diğerlerinden bağımsız uygulanabilir.
5. **K7** — küçük SQL değişikliği, mevcut sessiz kör noktayı kapatıyor.
6. Yüksek/Orta tier — sprint planına dağıtılabilir, hiçbiri acil canlı risk taşımıyor.
