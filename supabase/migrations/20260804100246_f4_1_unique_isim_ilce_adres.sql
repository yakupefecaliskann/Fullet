-- F4-1 (4 Ağustos 2026): unique(isim, il, ilce) yanlış bir varsayım yapıyordu.
--
-- Varsayım: "aynı ilçede aynı isimli iki istasyon olamaz."
-- Gerçek:   bir şirket aynı ilçede birden fazla istasyon işletebilir.
--
-- Opet API'sinde 35 böyle kayıt var ve hepsi meşru. Örnek — Kırklareli/Babaeski:
--   MOLA PETROL ... "ORUÇLU KÖYÜ NO:144 EDİRNE YÖNÜ"
--   MOLA PETROL ... "ORUÇLU KÖYÜ 145F İSTANBUL YÖNÜ"
-- Bu tam olarak ProximityIdentityTest'in koruduğu durum: yol ayrımının iki
-- yanındaki AYRI istasyonlar. İstanbul/Beykoz'da aynı şirketin 3 istasyonu var.
--
-- Kısıt kaldırılmıyor, GENİŞLETİLİYOR. `adres` ayırt edici olarak ekleniyor;
-- ölçüldü: adres eklenince 1.246 kayıttaki çakışma 35 gruptan 1'e düşüyor.
--
-- NULLS NOT DISTINCT kritik: mevcut kayıtların çoğunun adresi NULL. Postgres
-- varsayılanında NULL <> NULL olduğu için kısıt o satırlarda tamamen etkisiz
-- kalırdı ve eski koruma sessizce kaybolurdu. NULLS NOT DISTINCT ile NULL'lar
-- eşit sayılır, yani adressiz satırlarda davranış (isim, il, ilce) ile aynı kalır.
--
-- Doğrulandı: mevcut veride yeni kısıtı ihlal eden 0 grup var.
-- Doğrulandı: `on_conflict` bu tabloda hiçbir yerde kullanılmıyor (yalnızca
-- fiyatlar tablosunda istasyon_id,yakit_tipi üzerinde).

ALTER TABLE public.istasyonlar DROP CONSTRAINT unique_isim_ilce;

ALTER TABLE public.istasyonlar
    ADD CONSTRAINT unique_isim_ilce_adres
    UNIQUE NULLS NOT DISTINCT (isim, il, ilce, adres);
