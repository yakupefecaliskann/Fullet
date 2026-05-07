-- Fullet Supabase base schema.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS istasyonlar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marka TEXT NOT NULL,
    isim TEXT NOT NULL,
    il TEXT,
    ilce TEXT,
    adres TEXT,
    enlem DOUBLE PRECISION,
    boylam DOUBLE PRECISION,
    konum GEOGRAPHY(POINT, 4326),
    aktif BOOLEAN NOT NULL DEFAULT TRUE,
    veri_kaynagi TEXT,
    olusturulma_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    guncellenme_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT istasyonlar_lat_lng_valid CHECK (
        (enlem IS NULL AND boylam IS NULL)
        OR (enlem BETWEEN 35 AND 43 AND boylam BETWEEN 25 AND 46)
    )
);

CREATE INDEX IF NOT EXISTS istasyonlar_konum_idx ON istasyonlar USING GIST(konum);
CREATE INDEX IF NOT EXISTS istasyonlar_brand_city_idx ON istasyonlar(marka, il, ilce);

CREATE TABLE IF NOT EXISTS fiyatlar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    istasyon_id UUID NOT NULL REFERENCES istasyonlar(id) ON DELETE CASCADE,
    yakit_tipi TEXT NOT NULL,
    fiyat NUMERIC(10, 2) NOT NULL CHECK (fiyat > 0 AND fiyat < 300),
    son_guncelleme TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    veri_kaynagi TEXT,
    CONSTRAINT fiyatlar_istasyon_yakit_unique UNIQUE(istasyon_id, yakit_tipi)
);

CREATE INDEX IF NOT EXISTS fiyatlar_istasyon_idx ON fiyatlar(istasyon_id);

CREATE TABLE IF NOT EXISTS fiyat_gecmisi (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    istasyon_id UUID NOT NULL REFERENCES istasyonlar(id) ON DELETE CASCADE,
    yakit_tipi TEXT NOT NULL,
    eski_fiyat NUMERIC(10, 2),
    yeni_fiyat NUMERIC(10, 2) NOT NULL,
    fiyat_farki NUMERIC(10, 2),
    degisim_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS fiyat_gecmisi_istasyon_tarih_idx
ON fiyat_gecmisi(istasyon_id, degisim_tarihi DESC);
