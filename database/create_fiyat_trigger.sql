-- 1. Fiyat değiştiğinde devreye girecek olan fonksiyon (Stored Procedure)
CREATE OR REPLACE FUNCTION log_fiyat_degisimi()
RETURNS trigger AS $$
BEGIN
  -- Eski fiyat varsa ve yeni fiyat eskisinden farklıysa çalışır
  IF (OLD.fiyat IS DISTINCT FROM NEW.fiyat) THEN
    INSERT INTO fiyat_gecmisi (
      istasyon_id, 
      yakit_tipi, 
      eski_fiyat, 
      yeni_fiyat, 
      fiyat_farki, 
      degisim_tarihi
    ) VALUES (
      OLD.istasyon_id,
      OLD.yakit_tipi,
      OLD.fiyat,
      NEW.fiyat,
      ROUND(NEW.fiyat - OLD.fiyat, 2), -- Fark pozitifse ZAM, negatifse İNDİRİM
      NOW()
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Herhangi bir çakışmaya karşı varsa eski trigger'ı siliyoruz
DROP TRIGGER IF EXISTS trigger_fiyat_guncelleme ON fiyatlar;

-- 3. Trigger'ımız. Fiyatlar tablosunda "UPDATE" (Güncelleme) olduğunda otomatik tetiklenecek.
CREATE TRIGGER trigger_fiyat_guncelleme
AFTER UPDATE ON fiyatlar
FOR EACH ROW
EXECUTE FUNCTION log_fiyat_degisimi();
