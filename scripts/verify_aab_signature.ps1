<#
.SYNOPSIS
    Bir AAB/APK'nin hangi sertifikayla imzalandigini gosterir ve beklenen upload
    sertifikasiyla karsilastirir.

.DESCRIPTION
    Bu kontrol bos yere yazilmadi: 31 Temmuz 2026'da uretilen app-release.aab,
    upload anahtari yerine bir "Smoke Test" sertifikasiyla (CN=Smoke Test, OU=Test)
    imzalanmisti ve bu ancak yayin oncesi denetimde fark edildi. Play, yanlis
    anahtarla imzalanmis paketi reddeder; paket imzasizsa da reddeder.

    Script imza blogunu (META-INF/*.RSA|DSA|EC) AAB icinden cikarir ve SHA-1
    parmak izini beklenen degerle karsilastirir.

.PARAMETER Path
    AAB veya APK dosyasinin yolu. Varsayilan: son uretilen release bundle.

.PARAMETER ExpectedSha1
    Beklenen upload sertifikasi SHA-1'i. Varsayilan, Play Console'a kayitli deger.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\verify_aab_signature.ps1
#>
param(
    [string]$Path = "",
    # Yeni upload sertifikasi (4 Agustos 2026'da uretildi; eski anahtar
    # kaybedildigi icin Play Console'dan "upload key reset" talep edilecek).
    [string]$ExpectedSha1 = "497B9CC2DF7F949365F6B80A35CB7F9444CD67E2"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($Path)) {
    $Path = Join-Path $Root "fullet_flutter\build\app\outputs\bundle\release\app-release.aab"
}

if (-not (Test-Path $Path)) {
    Write-Host "[HATA] Paket bulunamadi: $Path" -ForegroundColor Red
    exit 1
}

$item = Get-Item $Path
Write-Host ""
Write-Host "Paket : $($item.FullName)"
Write-Host "Boyut : $([math]::Round($item.Length / 1MB, 1)) MB"
Write-Host "Tarih : $($item.LastWriteTime)"
Write-Host ""

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($item.FullName)
try {
    # Imza blogu yalnizca KOK META-INF altindadir. `base/root/META-INF/...`
    # altindakiler uygulamanin kendi kaynaklaridir, imza degildir.
    $sigEntry = $zip.Entries | Where-Object {
        $_.FullName -match '^META-INF/[^/]+\.(RSA|DSA|EC)$'
    } | Select-Object -First 1

    if ($null -eq $sigEntry) {
        Write-Host "[BASARISIZ] Paket IMZASIZ." -ForegroundColor Red
        Write-Host "  android/key.properties eksik olabilir." -ForegroundColor Red
        Write-Host "  Bkz. GOOGLE_PLAY_LAUNCH_CHECKLIST.md ss.2.1" -ForegroundColor Red
        exit 1
    }

    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("fullet_sig_" + [guid]::NewGuid().ToString("N") + ".bin")
    try {
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($sigEntry, $tmp, $true)
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($tmp)
    } finally {
        if (Test-Path $tmp) { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    }
} finally {
    $zip.Dispose()
}

$actual = $cert.Thumbprint.ToUpper()
$expected = ($ExpectedSha1 -replace '[^0-9A-Fa-f]', '').ToUpper()

function Format-Sha1([string]$hex) {
    return (($hex -split '(..)' | Where-Object { $_ }) -join ':')
}

Write-Host "Imza blogu : $($sigEntry.FullName)"
Write-Host "Subject    : $($cert.Subject)"
Write-Host "Gecerlilik : $($cert.NotBefore.ToString('yyyy-MM-dd')) -> $($cert.NotAfter.ToString('yyyy-MM-dd'))"
Write-Host "SHA-1      : $(Format-Sha1 $actual)"
Write-Host "Beklenen   : $(Format-Sha1 $expected)"
Write-Host ""

if ($actual -eq $expected) {
    Write-Host "[OK] Paket beklenen upload sertifikasiyla imzalanmis." -ForegroundColor Green
    exit 0
}

Write-Host "[BASARISIZ] Paket YANLIS anahtarla imzalanmis. Play bunu reddeder." -ForegroundColor Red
if ($cert.Subject -match 'Smoke|Test') {
    Write-Host "  Sertifika bir test/gecici anahtar gibi gorunuyor." -ForegroundColor Yellow
}
Write-Host "  android/key.properties dogru keystore'u gosteriyor mu kontrol et." -ForegroundColor Red
exit 1
