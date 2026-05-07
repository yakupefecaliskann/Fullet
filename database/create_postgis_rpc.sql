-- PostGIS konum altyapisi ve harita RPC fonksiyonu.

CREATE EXTENSION IF NOT EXISTS postgis;

UPDATE istasyonlar
SET konum = ST_SetSRID(ST_MakePoint(boylam, enlem), 4326)::geography
WHERE boylam IS NOT NULL
  AND enlem IS NOT NULL
  AND konum IS NULL;

CREATE OR REPLACE FUNCTION set_istasyon_konum()
RETURNS trigger AS $$
BEGIN
  IF NEW.boylam IS NOT NULL AND NEW.enlem IS NOT NULL THEN
    NEW.konum := ST_SetSRID(ST_MakePoint(NEW.boylam, NEW.enlem), 4326)::geography;
  ELSE
    NEW.konum := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_konum ON istasyonlar;

CREATE TRIGGER trigger_set_konum
BEFORE INSERT OR UPDATE OF enlem, boylam ON istasyonlar
FOR EACH ROW
EXECUTE FUNCTION set_istasyon_konum();

CREATE INDEX IF NOT EXISTS istasyonlar_konum_idx ON istasyonlar USING GIST(konum);

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
    AND lat BETWEEN 35 AND 43
    AND lng BETWEEN 25 AND 46
    AND ST_DWithin(
      konum,
      ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
      LEAST(GREATEST(max_dist_meters, 1000), 100000)
    )
  ORDER BY konum <-> ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
  LIMIT LEAST(GREATEST(max_results, 1), 500);
$$;

GRANT EXECUTE ON FUNCTION get_nearby_stations(DOUBLE PRECISION, DOUBLE PRECISION, INT, INT) TO anon, authenticated;
