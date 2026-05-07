# Fullet Gizlilik Politikası Taslağı

Bu metin Google Play'e yüklemeden önce public, aktif ve PDF olmayan bir URL'de yayınlanmalıdır.

## Uygulama

Fullet, Türkiye'deki akaryakıt istasyonlarını ve resmi kaynaklardan alınan yakıt fiyatlarını harita üzerinde gösteren bir mobil uygulamadır.

## Toplanan ve Kullanılan Veriler

Fullet kullanıcı hesabı oluşturmaz, kullanıcı profili tutmaz ve reklam/analytics SDK'sı kullanmaz.

Uygulama aşağıdaki verileri kullanabilir:

- Konum verisi: Yakındaki istasyonları bulmak, mesafe hesaplamak ve haritayı kullanıcının çevresine taşımak için kullanılır. Konum geçmişi tutulmaz.
- Yakıt ve araç tercihleri: Seçili yakıt türü, yakıt tüketimi, depo hacmi ve garaj tercihleri cihazda yerel olarak saklanır.
- Favoriler ve son bakılan istasyonlar: Uygulama deneyimini kişiselleştirmek için cihazda yerel olarak saklanır.
- Ağ istekleri: İstasyon, fiyat ve haber verilerini göstermek için Supabase ve ilgili servislerden veri okunur.

## Verilerin Paylaşımı

Yakındaki istasyonları hesaplamak için konum koordinatı backend sorgularında kullanılabilir. Fullet bu bilgiyi kullanıcı profili oluşturmak veya konum geçmişi tutmak için kullanmaz.

Yol tarifi istendiğinde Google Maps açılabilir. Haber bağlantılarına tıklandığında dış tarayıcı veya ilgili haber sitesi açılabilir.

## Saklama ve Silme

Yerel tercihler cihazda saklanır. Kullanıcı uygulama verilerini cihaz ayarlarından temizleyerek bu bilgileri silebilir.

## Güvenlik

Uygulama ağ isteklerini HTTPS üzerinden yapar. Canlı fiyat ve istasyon verileri Supabase üzerinde tutulur. Supabase public erişimi sadece uygulamada gösterilmesi gereken okuma verileriyle sınırlanmalıdır.

## İletişim

Gizlilik soruları için yayın öncesinde geliştirici iletişim e-postası buraya eklenmelidir.

Son güncelleme: 2026-05-07
