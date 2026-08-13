@echo off
title Sistemi Sifirlama Araci
color 4F
echo =========================================
echo DIKKAT: SISTEM VERILERINI SIFIRLAMA
echo =========================================
echo.
echo Bu islem asagidakileri KALICI OLARAK silecektir:
echo - Tum gecmis ve gelecek randevular
echo - Tum usta ve calisan hesaplari
echo - Kisisel ayarlar, calisma saatleri
echo - Yuklenen profil fotograflari
echo.
echo Devam etmeden once calismakta olan "Berber Randevu Sistemi" 
echo (baslat.bat) siyah ekranini KAPATTIGINIZDAN EMIN OLUN!
echo Aksi takdirde dosyalar silinemeyebilir.
echo.
set /p onay="Her seyi tamamen silmek istediginize emin misiniz? (EVET yazip Enter'a basin): "

if /i "%onay%" neq "EVET" (
    echo.
    echo Islem IPTAL EDILDI. Verileriniz guvende.
    pause
    exit /b
)

echo.
echo Veritabani dosyasi siliniyor...
if exist berber.db (
    del berber.db
    echo Veritabani basariyla silindi.
) else (
    echo Veritabani zaten bos.
)

echo.
echo Profil fotograflari temizleniyor...
if exist static\images\profiles\* (
    del /Q static\images\profiles\*
    echo Profil fotograflari temizlendi.
)

echo.
echo =========================================
echo SISTEM BASARIYLA SIFIRLANDI!
echo =========================================
echo Sistemi yepyeni, sifirdan kurmak icin masaustundeki
echo 'baslat.bat' dosyasina tiklayabilirsiniz.
echo.
pause
