-- Add visibility and price status columns to implement enterprise data quality logic
-- Preserves backwards compatibility for the 'aktif' column

ALTER TABLE public.istasyonlar 
  ADD COLUMN IF NOT EXISTS visibility_status TEXT NOT NULL DEFAULT 'visible';

ALTER TABLE public.fiyatlar 
  ADD COLUMN IF NOT EXISTS price_status TEXT NOT NULL DEFAULT 'fresh';

-- Idempotent check constraints
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_visibility_status') THEN
        ALTER TABLE public.istasyonlar ADD CONSTRAINT chk_visibility_status CHECK (visibility_status IN ('visible', 'low_priority', 'hidden'));
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_price_status') THEN
        ALTER TABLE public.fiyatlar ADD CONSTRAINT chk_price_status CHECK (price_status IN ('fresh', 'stale', 'unknown'));
    END IF;
END $$;

-- Update existing data to default state
UPDATE public.istasyonlar SET visibility_status = 'visible' WHERE aktif = true AND visibility_status = 'visible';
UPDATE public.istasyonlar SET visibility_status = 'hidden' WHERE aktif = false AND visibility_status = 'visible';
UPDATE public.fiyatlar SET price_status = 'fresh' WHERE price_status = 'fresh';

NOTIFY pgrst, 'reload schema';
