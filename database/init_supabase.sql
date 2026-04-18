-- Fullet Akaryakıt Uygulaması - Supabase İnitialize Dosyası
-- Bu kod Supabase SQL Editörüne yapıştırılarak çalıştırılmalıdır.

-- 1. PostGIS eklentisini aktif et (Konum bazlı aramalar için)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. İstasyonlar Tablosu
CREATE TABLE istasyonlar (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    marka VARCHAR(50) NOT NULL, -- Örn: 'Shell', 'Opet'
    isim VARCHAR(255) NOT NULL,
    il VARCHAR(100),
    ilce VARCHAR(100),
    adres TEXT,
    -- Basit sorgulama icin standart koordinatlar
    enlem DECIMAL(10, 6),
    boylam DECIMAL(10, 6),
    -- PostGIS coğrafi nokta: (Boylam, Enlem)
    konum GEOGRAPHY(POINT, 4326), 
    olusturulma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Konum bazlı aramayı hızlandırmak için indeks (Haritada gezindikçe hızlı yanıt almak için)
CREATE INDEX istasyonlar_konum_idx ON istasyonlar USING GIST(konum);

-- 3. Anlık Fiyatlar Tablosu (Her istasyonun güncel fiyatları)
CREATE TABLE fiyatlar (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    istasyon_id UUID REFERENCES istasyonlar(id) ON DELETE CASCADE,
    yakit_tipi VARCHAR(50) NOT NULL, -- 'Kurşunsuz 95', 'Motorin', 'LPG' vb.
    fiyat DECIMAL(10, 2) NOT NULL,
    son_guncelleme TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(istasyon_id, yakit_tipi) -- Bir istasyonda bir yakıt tipinin sadece bir güncel fiyatı olur
);

-- 4. Fiyat Geçmişi Log Tablosu (Zam/İndirim bildirimleri için kritik)
CREATE TABLE fiyat_gecmisi (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    istasyon_id UUID REFERENCES istasyonlar(id) ON DELETE CASCADE,
    yakit_tipi VARCHAR(50) NOT NULL,
    eski_fiyat DECIMAL(10, 2),
    yeni_fiyat DECIMAL(10, 2) NOT NULL,
    fiyat_farki DECIMAL(10, 2), -- Pozitifse ZAM, Negatifse İNDİRİM
    degisim_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hızlı sorgular için indeksler
CREATE INDEX fiyat_gecmisi_tarih_idx ON fiyat_gecmisi(degisim_tarihi);
CREATE INDEX fiyat_gecmisi_istasyon_idx ON fiyat_gecmisi(istasyon_id);
