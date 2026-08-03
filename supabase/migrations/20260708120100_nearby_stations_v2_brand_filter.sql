-- !! SUPERSEDED — 20260708130000_nearby_stations_brand_filter.sql !!
-- Bu migration `get_nearby_stations`i 4 ARGUMANLI olarak tanimlar. Hemen
-- ardindan gelen 20260708130000 ayni fonksiyonu 5 argumanli (brand_filter
-- dahil) haliyle yeniden tanimlar ve bunu tamamen ezer. Sirayla uygulaninca
-- son durum DOGRUDUR; dosya yalnizca tarihsel kayit olarak duruyor.
-- TEK BASINA CALISTIRMA — iki overload birlikte kalirsa PostgREST cagriyi
-- cozemez ve uygulama sessizce tum-ulke fallback'ine duser.
-- Canli dogrulama (3 Agustos 2026): tek bir get_nearby_stations var (5 arg).

-- =============================================================================
-- Fullet: Gelişmiş RPC — istasyon + fiyat tek sorguda
-- =============================================================================
-- Eski get_nearby_stations yerine get_nearby_stations_v2 eklenir.
-- Flutter uygulaması 2 ayrı istek yerine tek RPC çağrısıyla
-- istasyon ve fiyat bilgisini aynı anda alır.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- -----------------------------------------------------------------------------
-- Eski RPC'yi koru (geriye dönük uyumluluk)
-- Flutter kodu güncellenmeden önce eski versiyon çalışmaya devam eder.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_nearby_stations(
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  max_dist_meters INT DEFAULT 20000,
  max_results INT DEFAULT 250
)
RETURNS SETOF istasyonlar
LANGUAGE sql
STABLE
AS $$
  SELECT *
  FROM istasyonlar
  WHERE konum IS NOT NULL
    AND visibility_status IN ('visible', 'low_priority')
    AND aktif = TRUE
    AND lat BETWEEN 35 AND 43
    AND lng BETWEEN 25 AND 46
    AND ST_DWithin(
      konum,
      ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
      LEAST(GREATEST(max_dist_meters, 1000), 100000)
    )
  ORDER BY konum <-> ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
  LIMIT LEAST(GREATEST(max_results, 1), 1000);
$$;

-- -----------------------------------------------------------------------------
-- Yeni RPC v2: İstasyon + Fiyat birleşik sorgu
-- Tek ağ isteğiyle istasyon bilgisi + tüm yakıt fiyatları gelir.
-- -----------------------------------------------------------------------------
-- CREATE OR REPLACE, argüman sayısını değiştiren bir imzayı "aynı fonksiyon"
-- saymaz (yeni parametreler DEFAULT'lu olsa bile) — bu yüzden eski 4 argümanlı
-- sürümü açıkça DROP ediyoruz, aksi halde iki overload birlikte kalırdı.
DROP FUNCTION IF EXISTS get_nearby_stations_v2(DOUBLE PRECISION, DOUBLE PRECISION, INT, INT);

CREATE OR REPLACE FUNCTION get_nearby_stations_v2(
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  max_dist_meters INT DEFAULT 20000,
  max_results INT DEFAULT 250,
  brand_filter TEXT[] DEFAULT NULL
)
RETURNS TABLE (
  -- İstasyon alanları
  id              UUID,
  marka           TEXT,
  isim            TEXT,
  il              TEXT,
  ilce            TEXT,
  adres           TEXT,
  enlem           DOUBLE PRECISION,
  boylam          DOUBLE PRECISION,
  visibility_status TEXT,
  distance_meters DOUBLE PRECISION,
  -- Yakıt fiyatları (JSON olarak, tüm tipler tek kolonda)
  prices          JSONB
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    s.id,
    s.marka,
    s.isim,
    s.il,
    s.ilce,
    s.adres,
    s.enlem,
    s.boylam,
    s.visibility_status,
    -- Mesafeyi metre cinsinden hesapla
    ROUND(
      ST_Distance(
        s.konum,
        ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
      )::NUMERIC,
      0
    )::DOUBLE PRECISION AS distance_meters,
    -- Tüm yakıt fiyatlarını tek JSON objesine topla
    -- Örnek: {"Kursunsuz 95": {"fiyat": 47.5, "status": "fresh", "guncelleme": "2024-06-01T..."}}
    COALESCE(
      (
        SELECT jsonb_object_agg(
          f.yakit_tipi,
          jsonb_build_object(
            'fiyat', f.fiyat,
            'status', f.price_status,
            'guncelleme', f.son_guncelleme
          )
        )
        FROM public.fiyatlar f
        WHERE f.istasyon_id = s.id
      ),
      '{}'::jsonb
    ) AS prices
  FROM public.istasyonlar s
  WHERE s.konum IS NOT NULL
    AND s.visibility_status IN ('visible', 'low_priority')
    AND s.aktif = TRUE
    AND lat BETWEEN 35 AND 43
    AND lng BETWEEN 25 AND 46
    AND (brand_filter IS NULL OR s.marka = ANY(brand_filter))
    AND ST_DWithin(
      s.konum,
      ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
      LEAST(GREATEST(max_dist_meters, 1000), 100000)
    )
  ORDER BY s.konum <-> ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
  LIMIT LEAST(GREATEST(max_results, 1), 1000);
$$;

-- Yetkilendirme
GRANT EXECUTE ON FUNCTION get_nearby_stations(DOUBLE PRECISION, DOUBLE PRECISION, INT, INT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_nearby_stations_v2(DOUBLE PRECISION, DOUBLE PRECISION, INT, INT, TEXT[]) TO anon, authenticated;

-- =============================================================================
-- Hız indexleri
-- =============================================================================
CREATE INDEX IF NOT EXISTS istasyonlar_konum_idx ON istasyonlar USING GIST(konum);
CREATE INDEX IF NOT EXISTS istasyonlar_visibility_aktif_idx ON istasyonlar(visibility_status, aktif);
-- Fiyat JOIN'ini hızlandır
CREATE INDEX IF NOT EXISTS fiyatlar_istasyon_status_idx ON fiyatlar(istasyon_id, price_status);
CREATE INDEX IF NOT EXISTS fiyatlar_son_guncelleme_idx ON fiyatlar(son_guncelleme DESC);

-- =============================================================================
-- Hızlı doğrulama
-- =============================================================================
SELECT
  COUNT(*) AS istasyon_sayisi,
  SUM(CASE WHEN prices != '{}'::jsonb THEN 1 ELSE 0 END) AS fiyatli_istasyon
FROM get_nearby_stations_v2(41.0082, 28.9784, 20000, 50);
