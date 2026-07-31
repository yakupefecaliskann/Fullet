-- Push token hardening: kimliksiz (anon) INSERT yetkisini kaldir.
-- Hicbir istemci (Flutter uygulamasi dahil) su an push_tokens'a yazmiyor
-- (Sprint 4'e kadar gercek cihaz token kaydi yok) — bu yuzden anon rolune
-- acik INSERT yalnizca kimliksiz doldurma (spam) riski tasiyan gereksiz
-- bir yuzeydi. authenticated rolu (gecerli Firebase/Supabase JWT sarti)
-- ayni CHECK kisitlariyla korunmaya devam ediyor, Sprint 4'teki gercek
-- token kaydi bunu kullanabilecek.

DROP POLICY IF EXISTS "anon insert push token" ON public.push_tokens;
DROP POLICY IF EXISTS "authenticated insert push token" ON public.push_tokens;

CREATE POLICY "authenticated insert push token"
ON public.push_tokens FOR INSERT
TO authenticated
WITH CHECK (
  length(token) BETWEEN 20 AND 4096
  AND COALESCE(provider, 'fcm') IN ('fcm', 'expo', 'apns')
);

REVOKE INSERT ON public.push_tokens FROM anon;

NOTIFY pgrst, 'reload schema';
