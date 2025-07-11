# Bullshitometer

Das Bullshitometer ist eine Webanwendung, die YouTube-Videos transkribiert und den Inhalt mithilfe eines Large Language Models (LLM) auf Faktentreue, Argumentationsqualität und manipulativen Stil analysiert.

## Funktionen

- **Transkription**: Lädt YouTube-Videos herunter und transkribiert den Inhalt.
- **LLM-Analyse**: Nutzt konfigurierbare LLM-Anbieter (z. B. OpenRouter, LM Studio, Ollama), um Behauptungen zu extrahieren und zu bewerten.
- **Metriken**: Generiert Bewertungen wie "Bullshit %", "Valid %" und "Niveau %".
- **Dashboard**: Speichert und zeigt Analyseergebnisse in einem übersichtlichen Dashboard.
- **Optionen**: Ermöglicht die Verwaltung von LLM-Anbietern und die Anpassung der Prompts und Anweisungen für die Analyse.

## Installation

Um das Bullshitometer lokal auszuführen, befolge diese Schritte.

### Voraussetzungen

Stelle sicher, dass die folgenden Tools auf deinem System installiert sind:

- Python 3.8 oder höher
- `yt-dlp`
- `ffmpeg`

Falls du ein Debian/Ubuntu-System verwendest, kannst du sie mit dem folgenden Befehl installieren:

```sh
sudo apt-get update
sudo apt-get install -y yt-dlp ffmpeg