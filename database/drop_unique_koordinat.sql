-- The live database had a legacy global coordinate uniqueness rule.
-- Different official brands can legitimately publish the same station coordinates,
-- so this rule blocks valid station inventory imports.

ALTER TABLE public.istasyonlar
DROP CONSTRAINT IF EXISTS unique_koordinat;

DROP INDEX IF EXISTS public.unique_koordinat;
