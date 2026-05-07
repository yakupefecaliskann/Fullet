-- Haberler tablosu.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS haberler (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baslik TEXT NOT NULL,
    link TEXT NOT NULL,
    kaynak TEXT,
    tarih TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    olusturulma_tarihi TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS haberler_link_unique_idx ON haberler(link);
CREATE INDEX IF NOT EXISTS haberler_tarih_idx ON haberler(tarih DESC);
