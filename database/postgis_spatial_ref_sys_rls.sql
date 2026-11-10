-- public.spatial_ref_sys: anon ve authenticated rollerinin YAZMA yetkisini kaldırır.
--
-- OKUMA YETKİSİNE DOKUNMAYIN. Bu betiğin önceki hâli `REVOKE ALL` yapıyor ve RLS'i
-- politikasız açıyordu. `get_nearby_stations*` SECURITY INVOKER çalışır ve
-- geography işlemleri SRID tanımını bu tablodan çağıranın rolüyle okur; okuma
-- kesilirse yakın istasyon sorguları büyük olasılıkla hata verir (harita boş).
-- Bu yüzden RLS açılırken herkese okuma politikası da eklenir.
--
-- Tablonun sahibi supabase_admin. "must be owner of table spatial_ref_sys"
-- hatası alınırsa hiçbir satır uygulanmaz (tek transaction); çözüm Supabase
-- Support'tur. DROP EXTENSION postgis ÇALIŞTIRMAYIN.
--
-- Uyguladıktan sonra anon ile get_nearby_stations_v2 çağrısını doğrulayın.
-- Geri alma:
--   DROP POLICY "public read spatial_ref_sys" ON public.spatial_ref_sys;
--   ALTER TABLE public.spatial_ref_sys DISABLE ROW LEVEL SECURITY;

BEGIN;

ALTER TABLE public.spatial_ref_sys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read spatial_ref_sys" ON public.spatial_ref_sys;
CREATE POLICY "public read spatial_ref_sys"
  ON public.spatial_ref_sys
  FOR SELECT
  TO anon, authenticated
  USING (true);

REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN
  ON TABLE public.spatial_ref_sys
  FROM anon, authenticated;

COMMIT;

NOTIFY pgrst, 'reload schema';

SELECT
  c.relrowsecurity AS rls_enabled,
  has_table_privilege('anon', c.oid, 'SELECT') AS anon_select_should_be_true,
  has_table_privilege('anon', c.oid, 'DELETE') AS anon_delete_should_be_false,
  has_table_privilege('authenticated', c.oid, 'DELETE') AS authenticated_delete_should_be_false
FROM pg_class c
WHERE c.oid = 'public.spatial_ref_sys'::regclass;
