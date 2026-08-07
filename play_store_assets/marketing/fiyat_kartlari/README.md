# Fiyat kartı şablonları

3 hazır şablon (W1 görevi): `card_1_zam.png`, `card_2_il_karsilastirma.png`,
`card_3_en_ucuz_5.png`. Marka rengi ve font `app_icon_512.png` /
`feature_graphic_1024x500_new.png` ile birebir eşleşiyor.

İçindeki sayılar **örnek veridir** — gerçek bir zam/karşılaştırma/liste olduğunda:

1. `gen_cards.js` içindeki ilgili değişkeni (örn. `+1,42`, il isimleri, istasyon
   listesi) güncelle,
2. `node gen_cards.js` çalıştır → HTML dosyaları yenilenir,
3. Headless Chrome ile PNG'ye çevir:
   ```
   chrome --headless=new --disable-gpu --hide-scrollbars --window-size=1080,1350 \
     --screenshot=card_1_zam.png card_1_zam.html
   ```

Ya da en hızlısı: gerçek sayıları Claude'a söyle, 15 dakikalık zam gecesi
protokolü (§10.1) için kartı anında yeniden üretsin.
