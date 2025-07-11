#!/bin/bash

# Das Skript stoppt, wenn ein Befehl fehlschlägt
set -e

echo "Starte das Bullshitometer..."

# 1. Aktiviere die virtuelle Umgebung
echo "Aktiviere die virtuelle Umgebung..."
source venv/bin/activate

# 2. Starte die Flask-Anwendung
echo "Starte die Flask-App..."
# Die Flask-App im Debug-Modus starten (app.run(debug=True) in app.py)
python3 app.py

# Wenn du einen produktiven Webserver wie Gunicorn verwenden möchtest,
# könntest du diese Zeile stattdessen nutzen:
# gunicorn --bind 0.0.0.0:5000 app:app