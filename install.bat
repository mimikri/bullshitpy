@echo off
setlocal enabledelayedexpansion

echo Starte die Installation für das Bullshitometer...
echo.

REM Hinweis: yt-dlp.exe und ffmpeg.exe müssen manuell im selben Ordner
REM wie dieses Skript oder im System-PATH platziert werden.
echo ACHTUNG: Stelle sicher, dass yt-dlp.exe und ffmpeg.exe in diesem Ordner sind.
echo.

echo Erstelle eine virtuelle Python-Umgebung...
python -m venv venv
if %ERRORLEVEL% neq 0 (
    echo Fehler beim Erstellen der virtuellen Umgebung.
    echo Überprüfe, ob Python korrekt installiert und im PATH ist.
    pause
    exit /b
)
echo.

echo Aktiviere die virtuelle Umgebung...
call venv\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo Fehler beim Aktivieren der venv.
    pause
    exit /b
)
echo.

echo Installiere Python-Abhängigkeiten aus requirements.txt...
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Fehler bei der Installation der Python-Pakete.
    echo Überprüfe die requirements.txt und deine Internetverbindung.
    pause
    exit /b
)
echo.

echo Installation abgeschlossen!
echo Du kannst das Projekt jetzt starten, indem du die start.bat-Datei ausführst.
echo.
pause