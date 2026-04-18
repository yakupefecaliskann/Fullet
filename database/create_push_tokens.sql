-- FOMO Bildirimleri icin Cihaz Token'larini Saklayacak Tablo
CREATE TABLE push_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token TEXT UNIQUE NOT NULL,
    olusturulma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hızlı token sorgulamalari icin indeks
CREATE INDEX IF NOT EXISTS push_tokens_token_idx ON push_tokens(token);
