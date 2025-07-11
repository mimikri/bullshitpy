# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import re
import subprocess
import requests
import os
import datetime
from pytube import YouTube
import whisper
import logging
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'videos.db'
CONFIG_FILE = 'config.json'

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load configuration from JSON file
def load_config():
    """
    Lädt die Konfiguration aus der Datei und stellt sicher,
    dass alle erforderlichen Schlüssel vorhanden sind, indem
    Standardwerte zusammengeführt werden.
    """
    default_config = {
        "providers": [
            {
                "name": "OpenRouter",
                "api_address": "https://openrouter.ai/api/v1/chat/completions",
                "model_api": "https://openrouter.ai/api/v1/models",
                "api_key": None
            },
            {
                "name": "LM Studio",
                "api_address": "http://localhost:1234/v1/chat/completions",
                "model_api": "http://localhost:1234/v1/models",
                "api_key": None
            },
            {
                "name": "Ollama",
                "api_address": "http://localhost:11434/v1/chat/completions",
                "model_api": "http://localhost:11434/v1/models",
                "api_key": None
            }
        ],
        "last_provider": "OpenRouter",
        "last_model": "mistralai/mistral-7b-instruct-v0.2",
        "output_language": "de",
        "template_texts": {
            "importance_scale": """Wichtigkeitsskala: 
      10/10 = Kernargument (Hoch) 
      3-7/10 = Unterstützende Behauptung (Mittel) 
      0-2/10 = Nebenaspekt (Niedrig)""",
            "rating_scale": """Bewertungsskala:
     ✔️ = 10/10 = Verifiziert
     ✔️🤔 = 5-9/10 = Plausible Spekulation
     ⚠️🤔 3-5/10 = Mäßige Spekulation
     ❌🤔 1-2/10 = Unplausible Spekulation
     ❌ = 0/10 = Widerlegt""",
            "niveau_assessment": """Niveau-Bewertung (max 100)
     Level = [ 
      1. **Methodische Qualität** (30% Gewicht):  
       - Struktur: Logischer Ablauf, kohärente Argumente, klare These.  
       - Gründlichkeit: Systematische Analyse, vermeidet Übervereinfachung.  
    2. **Terminologiegebrauch** (25% Gewicht):  
       - Präzision: Fachspezifische Begriffe korrekt verwendet.  
       - Raffinesse: Vermeidet repetitive/vage Sprache.  
    3. **Wissenschaftliche Argumentation** (30% Gewicht):  
       - Beweise: Behauptungen durch Daten/Beispiele gestützt.  
       - Logik: Keine Trugschlüsse (z. B. ad hominem, Strohmann).  
    4. **Genauigkeit & Tiefe** (15% Gewicht):  
       - Faktische Korrektheit.  
       - Konzeptionelle Tiefe (vermeidet Oberflächlichkeit).  

    **Strafpunkte**:  
    - **-20 Punkte**: Signifikante sachliche Fehler.  
    - **-15 Punkte**: Logische Mängel/Trugschlüsse.  
    - **-10 Punkte**: Übermäßig simples Vokabular/Inhalt.
      ]""",
    "user_prompt_template": """Analysiere das Video-Transkript:
    1. Zusammenfassung: 
       - 1 Absatz mit den Kernaussagen
       - Aufzählung aller Hauptargumente
       
    2. Extrahiere JEDE Behauptung als Tabellenzeile:
       - 'Behauptung': Wörtlicher Wortlaut
       - 'Quelle': [Position im Video | Zitat | Filminhalt]
       - 'Wichtigkeit': x/10
       - 'Bewertung': Nur für Kanalpositionen x/10
       - 'Begründung': Max. 1 Satz
    
    3. Gesamteinschätzung: 
       - Stärke der These, Qualität der Quellen, logische Konsistenz
       - Bullshitometer: % der fragwürdigen Kanal-Behauptungen (gewichteter Durchschnitt)
       - Validometer: % der überprüfbaren Aussagen
       - Niveau: % Bewertung der argumentativen Qualität (0-100)
    
    4. Analysiere den Gesamtstil des Videos und klassifiziere ihn zum Beispiel als manipulativ, objektiv, wissenschaftlich, Propaganda oder hobbyistisch."""
     
        }
    }
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            
            # Füge fehlende Schlüssel aus der Standardkonfiguration hinzu
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            
            # Füge fehlende Schlüssel im 'template_texts'-Dictionary hinzu
            if 'template_texts' in default_config and 'template_texts' in config:
                for sub_key in default_config['template_texts']:
                    if sub_key not in config['template_texts']:
                        config['template_texts'][sub_key] = default_config['template_texts'][sub_key]
                        
            return config
    except FileNotFoundError:
        logger.warning(f"'{CONFIG_FILE}' not found. Creating a default config file.")
        save_config(default_config)
        return default_config
    except json.JSONDecodeError:
        logger.error(f"Error decoding '{CONFIG_FILE}'. Check the file format. A default config will be created.")
        save_config(default_config)
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        logger.warning(f"'{CONFIG_FILE}' not found. Creating a default config file.")
        save_config(default_config)
        return default_config
    except json.JSONDecodeError:
        logger.error(f"Error decoding '{CONFIG_FILE}'. Check the file format. A default config will be created.")
        save_config(default_config)
        return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
            return True
    except Exception as e:
        logger.error(f"Failed to save config file: {str(e)}")
        return False

# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS video (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            channel_title TEXT NOT NULL,
            video_title TEXT NOT NULL,
            bullshit_percent REAL,
            valid_percent REAL,
            niveau_percent REAL,
            video_description TEXT NOT NULL,
            llm_model TEXT NOT NULL,
            llm_provider TEXT NOT NULL,
            video_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            transcript TEXT,
            analysis_html TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DATABASE)

def extract_metrics_from_html(html):
    metrics = {'bullshit': 999, 'valid': 999, 'niveau': 999}
    for metric, pattern in [
        ('bullshit', r'id="bullshitometer"[^>]+value="([\d.]+)"'),
        ('valid', r'id="validometer"[^>]+value="([\d.]+)"'),
        ('niveau', r'id="niveau"[^>]+value="([\d.]+)"')
    ]:
        match = re.search(pattern, html)
        if match:
            try:
                metrics[metric] = float(match.group(1))
            except ValueError:
                pass
    return metrics

def analyze_transcript(transcript, provider_name, model_name, video_id, details=None):
    today = datetime.datetime.now().strftime("%A, %B %d, %Y")
    
    config = load_config()
    providers = config.get('providers', [])
    template_texts = config.get('template_texts', {})
    output_language = config.get('output_language', 'de') 
     
    provider_info = next((p for p in providers if p['name'] == provider_name), None)
    if not provider_info:
        logger.error(f"Provider '{provider_name}' not found in config.")
        return None, "Provider not found"
    
    endpoint = provider_info['api_address']
    headers = {"Content-Type": "application/json"}
    
    # Zugriff auf den API-Schlüssel über das Provider-Objekt
    api_key = provider_info.get('api_key', None)
    if provider_name == 'OpenRouter':
        if not api_key:
            logger.error("OpenRouter API key is missing in config.")
            return None, "OpenRouter API key is missing"
        headers["Authorization"] = f"Bearer {api_key}"
        headers["HTTP-Referer"] = "bullshitometer"
        headers["X-Title"] = "Youtube Analyzer"
        
    lang_map = {
        'de': 'German',
        'en': 'English'
    }
    logger.debug(f"Language: {lang_map.get(output_language, 'German')}")
    system_prompt = f'''
    you are a professional youtube transcript content fact checker and analyst.
    Today is {today}. the answer has to be in the language: {lang_map.get(output_language, 'German')}!
    Output: Single HTML(no css) div ({lang_map.get(output_language, 'German')}) containing:
    1. Video Summary
    2. Claims Table (ALL assertions) with columns:
       <th> Claim </th><th> Source </th><th> Importance </th><th> Rating </th><th> Reasoning </th>
    3. Evaluation Metrics
    Structure:
    <div>
      <h1>Zusammenfassung</h1>
      <p>[Kern-Zusammenfassung]</p>
      <ul>[Aufzählung der Hauptargumente]</ul>
      
      <h1>Behauptungen</h1>
      <table>
        <tr><th>Behauptung</th><th>Wichtigkeit</th><th>Bewertung</th><th>Begründung</th></tr>
        <tr><td>[Behauptung]</td><td>[Wichtigkeit]</td><td>[Bewertung]</td><td>[Begründung]</td></tr>
        ...
        <tr><td>[Behauptung]</td><td>[Wichtigkeit]</td><td>[Bewertung]</td><td>[Begründung]</td></tr>
      </table>
      
      <h1>Gesamteinschätzung</h1>
      <p>[...]</p>
      
     <h1>Metriken</h1>
      <div>
      <label for="file">Bullshitometer:</label><progress id="bullshitometer" max="100" value="[bullshitpercent]">[bullshitpercent]%</progress>[bullshitpercent]%
    <label for="file">Validometer:</label><progress id="validometer" max="100" value="[validpercent]">[validpercent]%</progress>[validpercent]%
    <label for="file">Niveau:</label><progress id="niveau" max="100" value="[niveaupercent]">[niveaupercent]%</progress>[niveaupercent]%
       </div>
       <div>[Charakterisierung]</div>
    </div>

    {template_texts.get('importance_scale', 'Wichtigkeitsskala: ...')}

    {template_texts.get('rating_scale', 'Bewertungsskala: ...')}

    {template_texts.get('niveau_assessment', 'Niveau-Bewertung: ...')}
    '''
    
    user_prompt = f"""
    {template_texts.get('user_prompt_template','')}

    Video Titel: {details['title']}
    Kanal Titel: {details['channel_title']}
    Video Beschreibung: {details['description']}
    Transkript: {transcript}
    """
    
    logger.debug(f"Starting analysis with service: {provider_name}, model: {model_name}")
    
    payload = {
        'model': model_name,
        'temperature': 0.4,
        'seed': 42,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        'stream': False
    }
    
    try:
        logger.debug(f"Sending request to {endpoint}")
        response = requests.post(
            endpoint,
            headers=headers,
            data=json.dumps(payload),
            timeout=300
        )
        logger.debug(f"Received response: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API Error {response.status_code}: {response.text}")
            return None, response.text
            
        response_data = response.json()
        
        if not response_data.get('choices'):
            logger.error(f"Invalid response: Missing 'choices' key\nFull response: {response_data}")
            return None, "Invalid API response format."
            
        if not response_data['choices']:
            logger.error(f"Empty choices array in response\nFull response: {response_data}")
            return None, "Empty choices array in API response."
            
        first_choice = response_data['choices'][0]
        
        content = first_choice.get('message', {}).get('content')
        if not content:
            logger.error(f"Could not find content in response\nFull response: {response_data}")
            return None, "Content not found in API response."
            
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        return content, None
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        return None, f"Analysis failed: {str(e)}"

def download_and_transcribe(url):
    video_id = get_youtube_video_id(url)
    if not video_id:
        return None
    logger.debug(f"Starting download for video ID: {video_id}")
    tmp_audio = f'audio_{video_id}.m4a'
    final_mp3 = f'audio_{video_id}.mp3'
    
    try:
        subprocess.run([
            'yt-dlp',
            '-f', 'bestaudio',
            '-o', tmp_audio,
            url
        ], check=True, capture_output=True, text=True)
        
        subprocess.run([
            'ffmpeg',
            '-y',
            '-i', tmp_audio,
            '-ab', '32k',
            '-ac', '1',
            final_mp3
        ], check=True, capture_output=True, text=True)
        
        logger.debug("Starting transcription...")
        model = whisper.load_model("large-v3-turbo")
        result = model.transcribe(final_mp3, language='de')
        logger.debug(f"Transcription completed, length: {len(result['text'])} chars")
        
        os.unlink(tmp_audio)
        os.unlink(final_mp3)
        logger.debug("Temporary files cleaned up")
        
        return result['text']
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return None

from pytube import extract

def get_youtube_video_id(url):
    try:
        cmd = ['yt-dlp', '--get-id', url]
        video_id = subprocess.check_output(cmd, text=True).strip()
        logger.debug(f"Extracted video ID: {video_id} from URL: {url}")
        return video_id
    except Exception as e:
        logger.error(f"Failed to extract video ID: {str(e)}")
        return None

def get_video_details(video_id):
    try:
        logger.debug(f"Fetching details for video ID: {video_id}")
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        cmd = ['yt-dlp', '--skip-download', '--print-json', url]
        output = subprocess.check_output(cmd, text=True)
        data = json.loads(output)
        
        details = {
            'channel_id': data.get('channel_id', ''),
            'channel_title': data.get('channel', ''),
            'title': data.get('title', ''),
            'description': data.get('description', ''),
        }
        logger.debug(f"Video details fetched: {details}")
        return details
    except Exception as e:
        logger.error(f"Failed to get video details: {str(e)}")
        return None

@app.route('/')
def index():
    """
    Rendert die Startseite und lädt die Konfiguration,
    um Anbieter und das zuletzt verwendete Modell auszuwählen.
    """
    config = load_config()
    providers = config.get('providers', [])
    last_provider = config.get('last_provider')
    last_model = config.get('last_model')
    return render_template('index.html', providers=providers, last_provider=last_provider, last_model=last_model)


@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form['youtube_url']
    provider = request.form['provider']
    model = request.form['model']
    config = load_config()
    config['last_provider'] = provider
    config['last_model'] = model
    save_config(config)
    
    logger.debug(f"Analysis request for URL: {url}")
    logger.debug(f"Provider: {provider}, Model: {model}")
    
    video_id = get_youtube_video_id(url)
    if not video_id:
        return jsonify({'error': "Invalid YouTube URL"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT transcript, channel_id, video_description, video_title, channel_title FROM video WHERE video_id = ?", (video_id,))
    video_data = cursor.fetchone()
    
    if video_data:
        logger.debug(f"Found existing video in DB: {video_id}")
        details = {
            'channel_id': video_data[1],
            'channel_title': video_data[4],
            'title': video_data[3],
            'description': video_data[2],
        }
        transcript = video_data[0]
    else:
        logger.debug(f"No existing record for {video_id}, fetching details")
        details = get_video_details(video_id)
        if not details:
            return jsonify({'error': "Could not fetch video details"}), 500
        
        transcript = download_and_transcribe(url)
        if not transcript:
            return jsonify({'error': "Transcription failed"}), 500
    
    analysis, error = analyze_transcript(transcript, provider, model, video_id, details)
    if error:
        return jsonify({'error': error}), 500
    
    metrics = extract_metrics_from_html(analysis)
    logger.debug(f"Extracted metrics: {metrics}")
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO video (
                video_title, video_description, channel_title, channel_id,
                transcript, analysis_html, bullshit_percent, valid_percent, niveau_percent,
                llm_provider, llm_model, video_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            details['title'], details['description'], details['channel_title'], details['channel_id'],
            transcript, analysis, metrics['bullshit'], metrics['valid'], metrics['niveau'],
            provider, model, video_id
        ))
        conn.commit()
        logger.debug("Analysis saved to database")
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        return jsonify({'error': f"Failed to save analysis: {str(e)}"}), 500
    finally:
        conn.close()
    
    return jsonify({
        'analysis': analysis,
        'metrics': metrics
    })

@app.route('/api/providers')
def get_providers():
    config = load_config()
    providers = config.get('providers', [])
    return jsonify(providers)

@app.route('/api/models', methods=['POST'])
def get_models():
    data = request.json
    provider_name = data.get('provider_name')
    config = load_config()
    provider_info = next((p for p in config.get('providers', []) if p['name'] == provider_name), None)
    
    if not provider_info:
        return jsonify({"error": "Provider not found"}), 404
        
    url = provider_info['model_api']
    headers = {"Content-Type": "application/json"}
    
    # Zugriff auf den API-Schlüssel
    api_key = provider_info.get('api_key', None)
    if provider_name == 'OpenRouter':
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
    try:
        response = requests.get(url, headers=headers)
        if not response.ok:
            return jsonify({"error": f"Failed to fetch models: {response.status_code}"}), response.status_code
            
        data = response.json()
        models = []
        if provider_name == 'OpenRouter':
            models = [m['id'] for m in data.get('data', [])]
        else:
            models = data.get('data', []) # assuming LM Studio returns an array directly
            
        return jsonify(models)
    except Exception as e:
        return jsonify({"error": f"Error fetching models: {str(e)}"}), 500

@app.route('/delete_video', methods=['DELETE'])
def delete_video():
    video_id = request.args.get('id')
    if not video_id:
        return 'Missing video ID', 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM video WHERE id = ?", (video_id,))
        conn.commit()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting video: {str(e)}")
        return 'Server error', 500
    finally:
        conn.close()

@app.route('/overview')
def overview():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM video ORDER BY set_date DESC")
    videos = cursor.fetchall()
    conn.close()
    return render_template('overview.html', videos=videos)
    
@app.route('/options', methods=['GET', 'POST'])
def options():
    config = load_config()
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save_key':
            new_key = request.form.get('openrouter_key')
            for provider in config['providers']:
                if provider['name'] == 'OpenRouter':
                    provider['api_key'] = new_key
                    break
            if save_config(config):
                flash("OpenRouter key saved successfully!", "success")
            else:
                flash("Failed to save OpenRouter key.", "error")

        elif action == 'add_provider':
            provider_name = request.form.get('provider_name')
            api_address = request.form.get('api_address')
            model_api = request.form.get('model_api')
            api_key = request.form.get('api_key')
            if provider_name and api_address and model_api:
                config['providers'].append({
                    "name": provider_name,
                    "api_address": api_address,
                    "model_api": model_api,
                    "api_key": api_key if api_key else None
                })
                if save_config(config):
                    flash("New provider added successfully!", "success")
                else:
                    flash("Failed to add new provider.", "error")
            else:
                flash("All required provider fields are required.", "error")
                
        elif action == 'edit_provider':
            original_name = request.form.get('original_name')
            new_name = request.form.get('name')
            api_address = request.form.get('api_address')
            model_api = request.form.get('model_api')
            api_key = request.form.get('api_key')
            
            found = False
            for provider in config['providers']:
                if provider['name'] == original_name:
                    provider['name'] = new_name
                    provider['api_address'] = api_address
                    provider['model_api'] = model_api
                    provider['api_key'] = api_key if api_key else None
                    found = True
                    break
            
            if found:
                if save_config(config):
                    flash("Provider updated successfully!", "success")
                else:
                    flash("Failed to update provider.", "error")
            else:
                flash("Provider to edit not found.", "error")

        elif action == 'delete_provider':
            provider_name_to_delete = request.form.get('provider_name')
            config['providers'] = [p for p in config['providers'] if p['name'] != provider_name_to_delete]
            if save_config(config):
                flash("Provider deleted successfully!", "success")
            else:
                flash("Failed to delete provider.", "error")

        elif action == 'update_templates':
            if 'template_texts' not in config:
                config['template_texts'] = {}
            
            # Alle Formularfelder auslesen und in die Konfiguration speichern
            config['template_texts']['importance_scale'] = request.form.get('importance_scale')
            config['template_texts']['rating_scale'] = request.form.get('rating_scale')
            config['template_texts']['niveau_assessment'] = request.form.get('niveau_assessment')
            config['template_texts']['user_prompt_template'] = request.form.get('user_prompt_template')
            config['output_language'] = request.form.get('output_language') # Neuen Wert speichern

            if save_config(config):
                flash("Anweisungen erfolgreich aktualisiert!", "success")
            else:
                flash("Fehler beim Speichern der Anweisungen.", "error")

        return redirect(url_for('options'))

    return render_template('options.html', config=config)

if __name__ == '__main__':
    app.run(debug=True)