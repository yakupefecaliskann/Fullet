# Fullet Gizlilik Politikası

> ⚠️ **SÜPERSEDE EDİLDİ (12 Tem 2026):** Bu taslak GÜNCEL DEĞİL — "hesap yok, analitik SDK yok" iddiaları 16 Haziran 2026'da düzeltildi (uygulama Firebase Analytics + Crashlytics + isteğe bağlı Google girişi kullanıyor). **Güncel ve yayında olan metin: `admin_panel/public/privacy.html`** (canlıda: https://yakupefecaliskann.github.io/Fullet/privacy.html). Bu dosyayı referans alma; yalnızca tarihçe için duruyor.

Canlı URL: https://yakupefecaliskann.github.io/Fullet/privacy.html

Son güncelleme: 2026-05-09 (taslak — güncel metin için yukarıdaki uyarıya bak)

Bu metin Google Play için herkese açık, aktif ve PDF olmayan GitHub Pages sayfası olarak yayınlanır.

## Uygulama

Fullet, Türkiye'deki akaryakıt istasyonlarını, yakıt fiyatlarını ve akaryakıt piyasasına ilişkin haberleri kullanıcıya gösteren bir mobil uygulamadır. Uygulama hesap oluşturma, reklam izleme veya üçüncü taraf analiz SDK'sı kullanmaz.

## Toplanan ve Kullanılan Veriler

- Konum verisi: Yakındaki istasyonları bulmak, mesafe hesaplamak, haritayı kullanıcının çevresine taşımak ve yol tarifi akışını başlatmak için kullanılır. Fullet konum geçmişi tutmaz.
- Yerel tercihler: Yakıt tipi, araç tüketimi, depo hacmi, favori istasyonlar ve son bakılan istasyonlar uygulama deneyimini kişiselleştirmek için cihazda saklanabilir.
- Anonim uygulama sağlığı: Uygulama sürümü, platform ve anonim kurulum kimliği aktif cihaz sayısını ve uygulamanın çalışıp çalışmadığını ölçmek için Supabase'e gönderilebilir. Bu kimlik ad, telefon, e-posta veya reklam kimliği içermez.
- Ağ verisi: İstasyon, fiyat ve haber verileri Supabase üzerinden okunur. Fiyatlar resmi veya doğrudan marka kaynaklarından alınan ham verilere dayanır.

## Verilerin Paylaşımı

Yakındaki istasyonları hesaplamak için konum koordinatı backend sorgularında kullanılabilir. Bu bilgi kullanıcı profili oluşturmak veya geçmiş konum listesi tutmak için kullanılmaz.

Yol tarifi istendiğinde Google Maps açılabilir. Haber bağlantılarına dokunulduğunda dış tarayıcı veya ilgili haber sitesi açılabilir.

## Saklama ve Silme

Yerel tercihler cihazda saklanır. Kullanıcı cihaz ayarlarından uygulama verilerini temizleyerek bu bilgileri silebilir.

Anonim heartbeat kayıtları uygulama sağlığı ve aktif cihaz ölçümü için tutulur; kişisel iletişim bilgisi içermez.

## Güvenlik

Uygulama ağ isteklerini HTTPS üzerinden yapar. Supabase veritabanında yayın verilerine erişim Row Level Security politikalarıyla sınırlandırılır. Servis anahtarları mobil uygulama veya web admin paneline konulmaz.

## İletişim

Gizlilik soruları için fulletapp@gmail.com adresinden iletişime geçilebilir.
