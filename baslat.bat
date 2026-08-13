@echo off
echo Berber Randevu Sistemi Baslatiliyor...
echo Tarayicinizda http://127.0.0.1:5000 adresini acabilirsiniz.
start "" "http://127.0.0.1:5000"
venv\Scripts\python.exe app.py
pause
