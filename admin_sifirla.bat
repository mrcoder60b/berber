@echo off
title Berber Admin Sifre Sifirlama Araci
color 0b

echo ==============================================
echo       Berber Sistemi Admin Sifirlama
echo ==============================================
echo.
echo Lutfen yeni bilgilerinizi girerken Turkce karakter
echo (ı, O, u, s, c, g) KULLANMAMAYA ozen gosterin!
echo.

set /p username="Yeni Kullanici Adi (orn: admin): "
set /p password="Yeni Sifre (orn: admin123): "

echo.
echo Islem yapiliyor, lutfen bekleyin...
echo.

.\venv\Scripts\python.exe sifre_sifirla.py "%username%" "%password%"

echo.
echo ==============================================
echo Islemler tamamlandi. Pencereyi kapatabilirsiniz.
pause
