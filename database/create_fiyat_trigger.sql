-- Fiyat degisimi log trigger'i.

CREATE OR REPLACE FUNCTION log_fiyat_degisimi()
RETURNS trigger AS $$
BEGIN
  IF OLD.fiyat IS DISTINCT FROM NEW.fiyat THEN
    NEW.son_guncelleme := NOW();

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
      ROUND(NEW.fiyat - OLD.fiyat, 2),
      NOW()
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_fiyat_guncelleme ON fiyatlar;

CREATE TRIGGER trigger_fiyat_guncelleme
BEFORE UPDATE ON fiyatlar
FOR EACH ROW
EXECUTE FUNCTION log_fiyat_degisimi();
