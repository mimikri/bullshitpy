@echo off
title Bullshitometer Start Script
echo Starte das Bullshitometer...
echo.

echo Aktiviere die virtuelle Umgebung...
call .\venv\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo Fehler beim Aktivieren der venv. Installation fehlgeschlagen?
    pause
    exit /b
)
echo.

echo Starte die Flask-App...
python app.py

echo.
echo Skript beendet. Drücke eine beliebige Taste zum Schließen.
pause