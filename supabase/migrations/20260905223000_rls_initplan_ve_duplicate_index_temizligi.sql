-- Supabase Performance Advisor bulgularini kapatir.
--
-- 1) auth_rls_initplan: auth.jwt()/auth.uid() cagrilari RLS policy'lerinde
--    satir basina yeniden degerlendiriliyordu. (select auth.<fn>()) sarmalamasi
--    Postgres'in bunu initplan olarak bir kez hesaplamasini saglar. Davranis
--    degismiyor, ayni predicate.
-- 2) duplicate_index: public.istasyonlar uzerinde iki ozdes GIST index vardi
--    (istasyonlar_konum_idx, idx_istasyonlar_konum). Orijinal isim
--    (istasyonlar_konum_idx) init_supabase.sql / create_postgis_rpc.sql /
--    production_hardening.sql / live_public_schema_fix.sql icinde referans
--    aliniyor; sonradan eklenen kopya (idx_istasyonlar_konum) dusuruldu.

ALTER POLICY "kullanici kendi favorilerini yonetir" ON public.fullet_favorites
  USING (firebase_uid = ((select auth.jwt()) ->> 'sub'::text))
  WITH CHECK (firebase_uid = ((select auth.jwt()) ->> 'sub'::text));

ALTER POLICY "kullanici kendi profilini yonetir" ON public.fullet_users
  USING (firebase_uid = ((select auth.jwt()) ->> 'sub'::text))
  WITH CHECK (firebase_uid = ((select auth.jwt()) ->> 'sub'::text));

ALTER POLICY "kullanici kendi alarmlarini yonetir" ON public.price_alerts
  USING (user_id = ((select auth.jwt()) ->> 'sub'::text))
  WITH CHECK (user_id = ((select auth.jwt()) ->> 'sub'::text));

ALTER POLICY "Kullanıcı kendi favorilerini görebilir" ON public.user_favorites
  USING ((select auth.uid()) = user_id);

ALTER POLICY "Kullanıcı kendi profilini görebilir" ON public.user_profiles
  USING ((select auth.uid()) = id);

DROP INDEX IF EXISTS public.idx_istasyonlar_konum;
