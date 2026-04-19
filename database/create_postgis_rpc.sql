-- 1. Önce mevcut veritabanındaki "boş" konum verilerini hesaplayıp dolduruyoruz
UPDATE istasyonlar 
SET konum = ST_SetSRID(ST_MakePoint(boylam, enlem), 4326)::geography 
WHERE boylam IS NOT NULL AND enlem IS NOT NULL AND konum IS NULL;

-- 2. Yeni eklenecek veya Python ile güncellenecek istasyonların konumunu (Point) otomatik hesaplayacak fonksiyon
CREATE OR REPLACE FUNCTION set_istasyon_konum()
RETURNS trigger AS $$
BEGIN
  IF NEW.boylam IS NOT NULL AND NEW.enlem IS NOT NULL THEN
    NEW.konum := ST_SetSRID(ST_MakePoint(NEW.boylam, NEW.enlem), 4326)::geography;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Herhangi bir çakışmaya karşı eski trigger'ı siliyoruz
DROP TRIGGER IF EXISTS trigger_set_konum ON istasyonlar;

-- 4. Trigger'ı Aktif Ediyoruz: İstasyon güncellendiğinde/eklendiğinde otonom çalışır.
CREATE TRIGGER trigger_set_konum
BEFORE INSERT OR UPDATE OF enlem, boylam ON istasyonlar
FOR EACH ROW
EXECUTE FUNCTION set_istasyon_konum();

-- 5. THE MAGIC: Uygulamanın Çağıracağı Mükemmel PostGIS Stored Procedure (RPC)
CREATE OR REPLACE FUNCTION get_nearby_stations(
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  max_dist_meters INT DEFAULT 20000
) 
RETURNS SETOF istasyonlar 
LANGUAGE sql 
STABLE
AS $$
  SELECT *
  FROM istasyonlar
  WHERE konum IS NOT NULL
    AND ST_DWithin(
      konum, 
      ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography, 
      max_dist_meters
    )
  ORDER BY konum <-> ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
  LIMIT 50; -- Maksimum 50 istasyon döndürür, haritayı kasmamak için güvenlik sınırıdır.
$$;
