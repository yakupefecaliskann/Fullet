-- Fullet Aşama 4: Haberler Tablosu (FOMO Etkisi)
CREATE TABLE haberler (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    baslik VARCHAR(255) NOT NULL,
    link TEXT NOT NULL,
    kaynak VARCHAR(100) NOT NULL, -- Örn: 'NTV', 'Sözcü'
    tarih TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    olusturulma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Haberleri en yeniye göre sıralamak için indeks
CREATE INDEX haberler_tarih_idx ON haberler(tarih DESC);
