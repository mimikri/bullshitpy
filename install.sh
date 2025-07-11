#!/bin/bash

# Das Skript stoppt, wenn ein Befehl fehlschlägt
set -e

echo "Starte die Installation für das bullshitometer-Projekt..."

# 1. Installation der Systempakete
echo "Installiere yt-dlp und ffmpeg..."
# Abhängig vom Betriebssystem muss der Paketmanager angepasst werden.
# Dieses Beispiel ist für Debian/Ubuntu-basierte Systeme.
if command -v apt-get &> /dev/null
then
    sudo apt-get update
    sudo apt-get install -y yt-dlp ffmpeg
elif command -v brew &> /dev/null
then
    brew install yt-dlp ffmpeg
else
    echo "Warnung: Weder apt-get noch Homebrew gefunden. Bitte installiere yt-dlp und ffmpeg manuell."
    echo "Auf Debian/Ubuntu: sudo apt-get install yt-dlp ffmpeg"
    echo "Auf macOS (mit Homebrew): brew install yt-dlp ffmpeg"
fi

# 2. Erstelle und aktiviere eine virtuelle Python-Umgebung
echo "Erstelle eine virtuelle Python-Umgebung..."
# Prüfe, ob python3.12 verfügbar ist, andernfalls verwende python3
PYTHON_CMD="python3"
if command -v python3.12 &> /dev/null
then
    PYTHON_CMD="python3.12"
    echo "Verwende Python 3.12 für die virtuelle Umgebung."
else
    echo "Python 3.12 wurde nicht gefunden. Verwende die Standard-Python-Version."
fi

# Erstelle die virtuelle Umgebung
$PYTHON_CMD -m venv venv

# Aktiviere die virtuelle Umgebung
echo "Aktiviere die virtuelle Umgebung..."
source venv/bin/activate

# 3. Installiere Python-Abhängigkeiten
echo "Installiere Python-Abhängigkeiten aus requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installation abgeschlossen!"
echo "Du kannst das Projekt starten, indem du die virtuelle Umgebung aktivierst und die App ausführst:"
echo "source venv/bin/activate"
echo "python3 app.py"