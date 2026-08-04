-- F4 / şeffaflık katmanı (4 Ağustos 2026, kullanıcı kararı).
--
-- SORUN: Uygulama fiyatı "bu istasyonun fiyatı" gibi gösteriyordu. Ölçüm:
--   Ankara'daki 86 Shell istasyonunun TAMAMI tek fiyat (82,08 ₺).
--   Opet 22 istasyon -> 1 fiyat. Petrol Ofisi 4 -> 1. BP 2 -> 1.
--   6.718 fiyat satırının tamamı il bazlı kaynaklardan geliyor.
--
-- Fiyat UYDURMA değil: markanın o il için ilan ettiği resmi fiyat, kendi
-- API'sinden geliyor. Eksik olan, kullanıcıya bunun NE olduğunun söylenmemesi.
--
-- Kod içinde bu ayrım zaten vardı (`db_utils.normalize_scraped_item` ->
-- veri_kapsami: regional_official | station_official) ama veritabanına hiç
-- yazılmıyordu, dolayısıyla uygulamaya da geçmiyordu. Bu kolon o ayrımı
-- kalıcı hale getirir.
--
-- DEFAULT 'regional' güvenli: ölçüldü, bugünkü satırların %100'ü il bazlı.

ALTER TABLE public.fiyatlar
    ADD COLUMN fiyat_kapsami text NOT NULL DEFAULT 'regional';

ALTER TABLE public.fiyatlar
    ADD CONSTRAINT fiyat_kapsami_gecerli
    CHECK (fiyat_kapsami IN ('regional', 'station'));

COMMENT ON COLUMN public.fiyatlar.fiyat_kapsami IS
    'regional = markanın il geneli ilan fiyatı (bugün tüm satırlar böyle). '
    'station = o istasyondan doğrulanmış fiyat. Uygulama bunu kullanıcıya '
    'gösterir; kaynak değişmeden bu değer değişmemeli.';
