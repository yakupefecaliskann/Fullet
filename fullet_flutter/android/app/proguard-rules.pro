# Fullet — R8 kurallari (L4)
#
# Flutter'in gradle eklentisi kendi tutma kurallarini otomatik ekliyor
# (io.flutter.** ve kayitli eklentiler). Asagidakiler yalnizca R8'in
# gorunurluk analizinin ulasamadigi, calisma zamaninda yansima (reflection)
# ile cozulen noktalar icin.

# Google Play Core: Flutter'in deferred components koduna referans veriyor ama
# uygulama split-install kullanmiyor. Kurali koymazsak R8 "missing class"
# uyarilariyla derlemeyi durdurur.
-dontwarn com.google.android.play.core.**

# Firebase Crashlytics: stack trace'lerin okunabilir kalmasi icin kaynak dosya
# ve satir numaralari korunmali. Aksi halde H4 ile yeni bagladigimiz async
# hata raporlari isimsiz satirlar olarak gelir.
-keepattributes SourceFile,LineNumberTable
-keepattributes *Annotation*
-keep public class * extends java.lang.Exception

# Uygulamanin kendi Kotlin giris noktasi.
-keep class com.fullet.app.** { *; }

# --- flutter_local_notifications + Gson (24 Kasım 2026, denetim §H-K5) ---
# Eklenti zamanlanmış bildirimleri Gson ile SharedPreferences'a yazıp okuyor
# ve TypeToken'ın generic `Signature` bilgisine dayanıyor. R8 (AGP 8 tam mod)
# bunu silince `loadScheduledNotifications` "Missing type parameter" ile
# düşüyor; `cancel()` da onu çağırdığı için yakıt/garaj hatırlatıcıları 1.0.3'ten
# (R8'in açıldığı 4 Ağu 2026) beri HİÇ kurulamadı — Play'den kurulan 1.0.6'da
# logcat'te ve `dumpsys alarm`'da (0 kayıt) doğrulandı. Kurallar eklentinin
# README'sinin işaret ettiği Gson örneğinden + örnek uygulamadan.
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn sun.misc.**
-keep class * extends com.google.gson.TypeAdapter
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer
-keepclassmembers,allowobfuscation class * {
  @com.google.gson.annotations.SerializedName <fields>;
}
-keep,allowobfuscation,allowshrinking class com.google.gson.reflect.TypeToken
-keep,allowobfuscation,allowshrinking class * extends com.google.gson.reflect.TypeToken
# Gson eklentinin model sınıflarını yansımayla (alan adlarıyla) yazıyor; alan
# adları sürümler arasında değişirse önceden kaydedilmiş bildirimler okunamaz.
-keep class com.dexterous.** { *; }
