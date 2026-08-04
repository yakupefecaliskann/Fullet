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
