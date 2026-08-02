-- =============================================================================
-- Fullet: "İLÇE/İL" birleşik yazılmış `istasyonlar.il` değerlerini onar
-- =============================================================================
-- Supabase Dashboard > SQL Editor'da çalıştır. Idempotent'tir
-- (WHERE il LIKE '%/%' koşulu ikinci koşuda hiçbir satır bulmaz).
--
-- Sorun:
--   20 istasyonun `il` kolonu "MERAM/KONYA", "KECIOREN/ANKARA" gibi birleşik
--   yazılmıştı ve `ilce` boştu. `matching._station_targets` fiyat yazarken
--   `.eq("il", "KONYA")` sorguluyor; bu satırlar hiçbir sorguya uymuyordu.
--   Canlı ölçüm: 20 satırın 20'sinde de TAZE FİYAT YOK.
--
-- Kodda kalıcı çözüm:
--   normalization.split_province_district / normalize_province — ingest
--   yolunda (normalize_scraped_item, normalize_station_inventory_item) ve
--   okuma yolunda (_load_brand_stations) uygulanır, yani bu değerler bir
--   daha oluşmaz. Bu script yalnızca MEVCUT satırları düzeltir.
--
-- Karar: hangi tarafın il olduğu konuma göre değil 81 il listesine bakılarak
-- belirlenir; kaynaklar iki sırayı da kullanıyor.
--
-- ÇAKIŞMA UYARISI (2 Ağustos 2026 koşusunda gözlendi):
--   `istasyonlar` üzerinde `unique_isim_ilce (isim, il, ilce)` kısıtı var.
--   20 satırın 18'i sorunsuz taşındı; 2'si taşınamadı:
--     Petrol Ofisi  MERAM/KONYA      -> (Petrol Ofisi, KONYA, MERAM) dolu
--     Petrol Ofisi  MERZIFON/AMASYA  -> (Petrol Ofisi, AMASYA, MERZIFON) dolu
--   Bu ikisi KOPYA DEĞİL: koordinatları hedeflerinden 2,4 km ve 3,5 km uzakta,
--   yani gerçek ve ayrı istasyonlar. Asıl kusur kısıtın kendisinde:
--   `isim` bu markalarda istasyon adı değil MARKA adı olduğu için, aynı
--   ilçedeki iki Petrol Ofisi istasyonu şemada temsil edilemiyor.
--   Bu script o satırlara DOKUNMAZ (aşağıdaki NOT EXISTS koşulu) — kısıtı
--   değiştirmek istasyon kimliği/dedupe mantığını (_bulk_write_station_inventory)
--   etkileyen ayrı bir karardır.
-- =============================================================================

WITH provinces(ad) AS (
  SELECT unnest(ARRAY[
    'ADANA','ADIYAMAN','AFYONKARAHISAR','AGRI','AKSARAY','AMASYA','ANKARA',
    'ANTALYA','ARDAHAN','ARTVIN','AYDIN','BALIKESIR','BARTIN','BATMAN',
    'BAYBURT','BILECIK','BINGOL','BITLIS','BOLU','BURDUR','BURSA','CANAKKALE',
    'CANKIRI','CORUM','DENIZLI','DIYARBAKIR','DUZCE','EDIRNE','ELAZIG',
    'ERZINCAN','ERZURUM','ESKISEHIR','GAZIANTEP','GIRESUN','GUMUSHANE',
    'HAKKARI','HATAY','IGDIR','ISPARTA','ISTANBUL','IZMIR','KAHRAMANMARAS',
    'KARABUK','KARAMAN','KARS','KASTAMONU','KAYSERI','KILIS','KIRIKKALE',
    'KIRKLARELI','KIRSEHIR','KOCAELI','KONYA','KUTAHYA','MALATYA','MANISA',
    'MARDIN','MERSIN','MUGLA','MUS','NEVSEHIR','NIGDE','ORDU','OSMANIYE',
    'RIZE','SAKARYA','SAMSUN','SANLIURFA','SIIRT','SINOP','SIRNAK','SIVAS',
    'TEKIRDAG','TOKAT','TRABZON','TUNCELI','USAK','VAN','YALOVA','YOZGAT',
    'ZONGULDAK'])
), parsed AS (
  SELECT
    i.id,
    btrim(split_part(i.il, '/', 1)) AS sol,
    btrim(split_part(i.il, '/', 2)) AS sag
  FROM public.istasyonlar i
  WHERE i.il LIKE '%/%'
    AND array_length(string_to_array(i.il, '/'), 1) = 2
), cozum AS (
  SELECT
    p.id,
    p.isim,
    CASE WHEN p.sag IN (SELECT ad FROM provinces)
              AND p.sol NOT IN (SELECT ad FROM provinces) THEN p.sag
         WHEN p.sol IN (SELECT ad FROM provinces)
              AND p.sag NOT IN (SELECT ad FROM provinces) THEN p.sol
    END AS yeni_il,
    CASE WHEN p.sag IN (SELECT ad FROM provinces)
              AND p.sol NOT IN (SELECT ad FROM provinces) THEN p.sol
         WHEN p.sol IN (SELECT ad FROM provinces)
              AND p.sag NOT IN (SELECT ad FROM provinces) THEN p.sag
    END AS yeni_ilce
  FROM parsed p
), sirali AS (
  -- Aynı hedef anahtara giden birden fazla satırdan yalnızca birini taşı.
  SELECT c.*,
         row_number() OVER (PARTITION BY c.isim, c.yeni_il, c.yeni_ilce
                            ORDER BY c.id) AS sira
  FROM cozum c
  WHERE c.yeni_il IS NOT NULL   -- iki taraf da il ise (belirsiz) DOKUNMA
), tasinabilir AS (
  SELECT s.* FROM sirali s
  WHERE s.sira = 1
    AND NOT EXISTS (               -- unique_isim_ilce çakışmasını önle
      SELECT 1 FROM public.istasyonlar x
      WHERE x.isim = s.isim AND x.il = s.yeni_il AND x.ilce = s.yeni_ilce)
)
UPDATE public.istasyonlar i
SET il  = t.yeni_il,
    -- Mevcut ilçe doluysa ona dokunma; yalnızca boşsa birleşik değerden kurtar.
    ilce = COALESCE(NULLIF(i.ilce, ''), t.yeni_ilce)
FROM tasinabilir t
WHERE i.id = t.id;

-- Doğrulama: yalnızca yukarıda açıklanan çakışan satırlar kalmalı
-- (2 Ağustos 2026 koşusunda: 2 satır, ikisi de Petrol Ofisi).
SELECT id, marka, isim, il, ilce FROM public.istasyonlar WHERE il LIKE '%/%';
