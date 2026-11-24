-- =============================================================================
-- PostGIS public -> extensions şemasına taşındı (24 Kasım 2026, denetim §H-G2)
-- =============================================================================
-- Sorun: PostGIS `public`'te kurulu olduğu için `public.spatial_ref_sys`
-- (sahibi supabase_admin) anon/authenticated rollerine INSERT/UPDATE/DELETE/
-- TRUNCATE yetkisiyle Data API'ye açıktı. Anon anahtarı olan herkes SRID
-- satırlarını silip `get_nearby_stations*` coğrafya sorgularını bozabilirdi.
-- Yetkiyi yalnızca sahip geri alabiliyor; Supabase Support (SU-547101, 11 Kas)
-- yetkiyle oynamayı değil eklentiyi `extensions` şemasına taşımayı önerdi.
-- `extensions` Data API'ye açık değil, uyarı da açık da kapanıyor.
--
-- Canlı ölçüm (24 Kas 2026, SQL Editor, salt okunur):
--   * postgis 3.3.7, schema=public, relocatable=false (ALTER EXTENSION ...
--     SET SCHEMA çalışmaz; DROP + CREATE şart)
--   * Eklenti dışı bağımlılar YALNIZCA: istasyonlar.konum (geography) ve
--     istasyonlar_konum_idx. `konum` enlem/boylam'dan türetilir -> veri kaybı yok.
--   * get_nearby_stations, get_nearby_stations_v2 ve set_istasyon_konum
--     `search_path=public` ile sabitlenmiş: taşımadan sonra ST_* ve geography
--     çözülemez, harita kırılır. Bu yüzden search_path GERİ DOLDURMADAN ÖNCE
--     `public, extensions` yapılıyor (BEFORE tetikleyici backfill'de çalışır).
--
-- Tek transaction: herhangi bir adım ya da sondaki doğrulama düşerse hiçbir
-- şey değişmez. Kilit süresince (birkaç saniye) RPC çağrıları bekler.
-- =============================================================================

BEGIN;

DROP EXTENSION postgis CASCADE;
CREATE EXTENSION postgis WITH SCHEMA extensions;

ALTER FUNCTION public.set_istasyon_konum()
  SET search_path = public, extensions;
ALTER FUNCTION public.get_nearby_stations(double precision, double precision, integer, integer, text[])
  SET search_path = public, extensions;
ALTER FUNCTION public.get_nearby_stations_v2(double precision, double precision, integer, integer)
  SET search_path = public, extensions;

ALTER TABLE public.istasyonlar
  ADD COLUMN konum extensions.geography(Point, 4326);

UPDATE public.istasyonlar
   SET konum = extensions.ST_SetSRID(extensions.ST_MakePoint(boylam, enlem), 4326)::extensions.geography
 WHERE enlem IS NOT NULL AND boylam IS NOT NULL;

CREATE INDEX istasyonlar_konum_idx ON public.istasyonlar USING GIST (konum);

-- Doğrulama: biri tutmazsa transaction tümden geri alınır.
DO $$
DECLARE
  eksik int;
  yakin int;
  yakin_v2 int;
BEGIN
  SELECT count(*) INTO eksik FROM public.istasyonlar
   WHERE enlem IS NOT NULL AND boylam IS NOT NULL AND konum IS NULL;
  IF eksik > 0 THEN
    RAISE EXCEPTION 'konum doldurulamadi: % satir', eksik;
  END IF;

  SELECT count(*) INTO yakin
    FROM public.get_nearby_stations(lat => 41.0082, lng => 28.9784,
                                    max_dist_meters => 20000, max_results => 50);
  SELECT count(*) INTO yakin_v2
    FROM public.get_nearby_stations_v2(41.0082, 28.9784, 20000, 50);
  IF yakin = 0 OR yakin_v2 = 0 THEN
    RAISE EXCEPTION 'yakin istasyon RPC bos dondu (v1=%, v2=%)', yakin, yakin_v2;
  END IF;

  IF to_regclass('public.spatial_ref_sys') IS NOT NULL THEN
    RAISE EXCEPTION 'public.spatial_ref_sys hala var';
  END IF;
END $$;

COMMIT;

NOTIFY pgrst, 'reload schema';
