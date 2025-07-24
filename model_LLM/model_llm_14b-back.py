# model_llm_14b.py
# -*- coding: utf-8 -*-
#cuuuuuuuuuuuuuuuuuuuuuuuuuuuu
from flask import Flask, request, jsonify, render_template_string, Response, send_from_directory
import pandas as pd
import requests
import os
import subprocess
import time
import threading
import json
import tabulate # Assurez-vous que c'est installé (pip install tabulate)
from prometheus_client import generate_latest, Counter, Histogram, Gauge, REGISTRY 

app = Flask(__name__)

# --- Configuration (pour l'API Ollama externe via Kubernetes) ---
OLLAMA_API_BASE_URL = os.getenv('OLLAMA_URL', 'http://ollama-service:11434')  # Service Kubernetes
LLM_API_URL = f"{OLLAMA_API_BASE_URL}/api/generate"
MODEL_NAME = "qwen2:0.5b"
MERGED_CSV_FILENAME = 'final_merged_data.csv'
FILE_PATH_IN_CONTAINER = f'{MERGED_CSV_FILENAME}'


# --- Chargement des données ---
df_merged_data = None
ollama_ready = False
data_loaded = False

def load_data_and_set_status():
    global df_merged_data, ollama_ready, data_loaded

    # Vérification simple de la disponibilité d'Ollama (service externe)
    print("Vérification de la disponibilité d'Ollama...")
    for attempt in range(60):  # Essayer pendant 60 secondes pour Kubernetes
        try:
            response = requests.get(f"{OLLAMA_API_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                print("Ollama est opérationnel.")
                ollama_ready = True
                break
        except requests.exceptions.RequestException:
            print(f"Tentative {attempt + 1}/60: Ollama n'est pas encore prêt...")
            time.sleep(1)
    
    if not ollama_ready:
        print("AVERTISSEMENT: Ollama n'est pas accessible après 60 tentatives.")
        return

    # Charger les données CSV (reste identique)
    print(f"Chargement du fichier de données fusionnées : {MERGED_CSV_FILENAME}...")
    if os.path.exists(FILE_PATH_IN_CONTAINER):
        try:
            df_merged_data = pd.read_csv(FILE_PATH_IN_CONTAINER)
            print("Fichier CSV fusionné chargé avec succès.")
            print(f"Nombre de lignes dans les données : {len(df_merged_data)}")
            print("Colonnes disponibles :", df_merged_data.columns.tolist())
            data_loaded = True
        except Exception as e:
            print(f"ERREUR lors du chargement du fichier CSV '{MERGED_CSV_FILENAME}' à {FILE_PATH_IN_CONTAINER} : {e}")
    else:
        print(f"ERREUR: Fichier CSV non trouvé au chemin spécifié : {FILE_PATH_IN_CONTAINER}")


# --- Fonction pour construire le prompt pour le LLM (unchanged) ---
def build_llm_prompt(user_question, dataframe):
    """
    Construit le prompt complet comme une seule chaîne pour l'endpoint /api/generate,
    en utilisant les marqueurs de chat du modèle ( ，)
    pour structurer les instructions système, le contexte et la question utilisateur.
    """
    system_instruction = """Tu es un assistant expert en analyse de logs systèmes.
Ton objectif est d'aider l'utilisateur à comprendre les logs et les résultats de détection d'anomalies (Isolation Forest et One-Class SVM) basés sur les données qu'il te fournit.
Réponds aux questions de l'utilisateur en te basant **strictement, précisément et en détail** sur les données de logs et les résultats que tu reçois comme contexte.
Mentionne les valeurs numériques (scores, indices, etc.) et les textes de logs pertinents présents dans les données pour justifier tes réponses.
Si une question porte sur des informations non présentes dans les données fournies, indique clairement que tu ne peux pas y répondre avec les données actuelles.
Sois concis, pertinent et utilise un ton informatif, mais privilégie l'exactitude et le détail basé sur les données.

**FORMAT DE RÉPONSE STRICT :**
1. Réponds **UNIQUEMENT** dans la langue de la question de l'utilisateur.
2. Ne commence ** JAMAIS** ta réponse par des commentaires sur ta démarche ou des pensées internes.
3. N'inclue **AUCUN** texte entre des balises comme <think>, <reasoning>, ou similaires.
4. Fournis **DIRECTEMENT** la réponse à la question posée, en t'appuyant sur les données du contexte.
"""

    context_data_string = ""
    if dataframe is not None and not dataframe.empty:
        context_data_string += "Aperçu des premières lignes des données disponibles :\n"
        context_data_string += dataframe.head().to_markdown(index=False) + "\n\n"

        cols_base = ['original_index', 'log_text', 'if_score', 'if_prediction', 'ocsvm_score', 'ocsvm_prediction', 'severity_unified_original_x']
        
        # Isolation Forest anomalies
        if 'if_score' in dataframe.columns and 'if_prediction' in dataframe.columns and 'original_index' in dataframe.columns:
            try:
                # Filtrer les logs prédits comme anomalies par IF (prediction == -1)
                if_anomalies = dataframe[dataframe['if_prediction'] == -1].copy()
                if not if_anomalies.empty:
                    # Prendre les 5 avec le score le plus bas (le plus anormal)
                    top_if_anomalies = if_anomalies.nsmallest(5, 'if_score', keep='all')
                    context_data_string += "Top 5 Logs considérés comme Anormaux par Isolation Forest (avec scores et prédictions) :\n"
                    cols_for_if_top = [col for col in ['original_index', 'log_text', 'if_score', 'if_prediction', 'ocsvm_score', 'ocsvm_prediction', 'severity_unified_original_x'] if col in top_if_anomalies.columns]
                    context_data_string += top_if_anomalies[cols_for_if_top].to_markdown(index=False) + "\n\n"
            except Exception as e:
               context_data_string += f"Avertissement : Erreur lors de la sélection des top IF anomalies : {e}\n\n"
               print(f"Avertissement : Erreur lors de la sélection des top IF anomalies : {e}")

        # One-Class SVM anomalies
        if 'ocsvm_score' in dataframe.columns and 'ocsvm_prediction' in dataframe.columns and 'original_index' in dataframe.columns:
            try:
                # Filtrer les logs prédits comme anomalies par OCSVM (prediction == -1)
                ocsvm_anomalies = dataframe[dataframe['ocsvm_prediction'] == -1].copy()
                if not ocsvm_anomalies.empty:
                    # Prendre les 5 avec le score le plus bas (le plus anormal)
                    top_ocsvm_anomalies = ocsvm_anomalies.nsmallest(5, 'ocsvm_score', keep='all')
                    context_data_string += "Top 5 Logs considérés comme Anormaux par One-Class SVM (avec scores et prédictions) :\n"
                    cols_for_ocsvm_top = [col for col in ['original_index', 'log_text', 'if_score', 'if_prediction', 'ocsvm_score', 'ocsvm_prediction', 'severity_unified_original_x'] if col in top_ocsvm_anomalies.columns]
                    context_data_string += top_ocsvm_anomalies[cols_for_ocsvm_top].to_markdown(index=False) + "\n\n"
            except Exception as e:
                context_data_string += f"Avertissement : Erreur lors de la sélection des top OCSVM anomalies : {e}\n\n"
                print(f"Avertissement : Erreur lors de la sélection des top OCSVM anomalies : {e}")
    else:
        context_data_string = "Aucune donnée n'est disponible comme contexte pour le modèle. Veuillez vérifier le chargement du CSV.\n"

    full_prompt = f"""  {system_instruction}

Données de contexte :
{context_data_string}

Question de l'utilisateur :
{user_question} 
"""
    return full_prompt


# --- Routes Flask pour l'interface web et l'API ---

@app.route('/')
def index():
    """Rend la page HTML principale de l'interface du chatbot."""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chatbot d'Analyse de Logs</title>
        <style>
            body { font-family: 'Arial', sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
            .chat-container { max-width: 800px; margin: 0 auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .messages { border: 1px solid #ddd; padding: 10px; min-height: 300px; max-height: 500px; overflow-y: auto; margin-bottom: 10px; border-radius: 4px; background-color: #e9e9e9; }
            .message { margin-bottom: 10px; padding: 8px; border-radius: 5px; }
            .user-message { background-color: #d1e7dd; text-align: right; }
            .bot-message { background-color: #f8d7da; text-align: left; }
            input[type="text"] { width: calc(100% - 100px); padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            button { width: 90px; padding: 10px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
            .spinner { display: none; margin-left: 10px; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .status-message { margin-top: 10px; padding: 10px; border-radius: 5px; background-color: #ffeeba; color: #856404; text-align: center;}
            .status-ok { background-color: #d4edda; color: #155724; }
            .status-error { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>Chatbot d'Analyse de Logs</h1>
            <div class="messages" id="messages"></div>
            <div class="status-message" id="status_message">Initialisation...</div>
            <div style="display: flex; margin-top: 10px;">
                <input type="text" id="user_input" placeholder="Votre question..." onkeydown="if(event.key === 'Enter') sendMessage()">
                <button onclick="sendMessage()">Envoyer</button>
                <div class="spinner" id="spinner"></div>
            </div>
        </div>

        <script>
            let ollamaReady = false;
            let dataLoaded = false;
            const statusMessageDiv = document.getElementById('status_message');
            const userInput = document.getElementById('user_input');
            const sendButton = document.querySelector('button');

            async function updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    ollamaReady = data.ollama_ready;
                    dataLoaded = data.data_loaded;

                    if (ollamaReady && dataLoaded) {
                        statusMessageDiv.textContent = 'Prêt à chatter !';
                        statusMessageDiv.className = 'status-message status-ok';
                        userInput.disabled = false;
                        sendButton.disabled = false;
                    } else if (ollamaReady && !dataLoaded) {
                        statusMessageDiv.textContent = 'Ollama est prêt, chargement des données...';
                        statusMessageDiv.className = 'status-message'; // Couleur par défaut/jaune
                        userInput.disabled = true;
                        sendButton.disabled = true;
                    }
                    else if (!ollamaReady && !dataLoaded) {
                        statusMessageDiv.textContent = "Demarrage de Ollama et chargement des donnees...";
                        statusMessageDiv.className = 'status-message';
                        userInput.disabled = true;
                        sendButton.disabled = true;
                    }
                    else { // Cas ollama pas prêt mais données chargées (improbable mais possible)
                        statusMessageDiv.textContent = "Attente du demarrage de Ollama...";
                        statusMessageDiv.className = 'status-message';
                        userInput.disabled = true;
                        sendButton.disabled = true;
                    }

                } catch (error) {
                    console.error('Erreur lors de la mise à jour du statut:', error);
                    statusMessageDiv.textContent = 'Erreur lors de la communication avec le serveur.';
                    statusMessageDiv.className = 'status-message status-error';
                    userInput.disabled = true;
                    sendButton.disabled = true;
                } finally {
                    // Mettre à jour le statut toutes les 2 secondes tant que tout n'est pas prêt
                    if (!(ollamaReady && dataLoaded)) {
                        setTimeout(updateStatus, 2000);
                    }
                }
            }

            // Lancer la mise à jour du statut au chargement de la page
            window.onload = updateStatus;

            async function sendMessage() {
                if (!ollamaReady || !dataLoaded) {
                    alert("Le chatbot nest pas encore pret. Veuillez patienter.");
                    return;
                }

                const userInput = document.getElementById('user_input');
                const messagesDiv = document.getElementById('messages');
                const spinner = document.getElementById('spinner');
                const messageText = userInput.value.trim();

                if (!messageText) return;

                // Afficher le message de l'utilisateur
                const userMessageDiv = document.createElement('div');
                userMessageDiv.className = 'message user-message';
                userMessageDiv.textContent = messageText;
                messagesDiv.appendChild(userMessageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll au bas

                userInput.value = ''; // Vider le champ de saisie
                spinner.style.display = 'inline-block'; // Afficher le spinner

                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ message: messageText })
                    });

                    const data = await response.json();

                    // Afficher la réponse du bot
                    const botMessageDiv = document.createElement('div');
                    botMessageDiv.className = 'message bot-message';
                    botMessageDiv.textContent = data.response || data.error || 'Erreur inconnue';
                    messagesDiv.appendChild(botMessageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll au bas

                } catch (error) {
                    console.error('Erreur:', error);
                    const errorMessageDiv = document.createElement('div');
                    errorMessageDiv.className = 'message bot-message';
                    errorMessageDiv.textContent = "Erreur: Impossible de communiquer avec le serveur chatbot.";
                    messagesDiv.appendChild(errorMessageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll au bas
                } finally {
                    spinner.style.display = 'none'; // Cacher le spinner
                }
            }
        </script>
    </body>
    </html>
    """)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Endpoint API pour traiter les requêtes du chatbot."""
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "Champ 'message' manquant"}), 400

    # Vérifier si les données ont été chargées
    if df_merged_data is None or not ollama_ready: # Ajout de la vérification ollama_ready
        return jsonify({"error": "Le service n'est pas encore entièrement prêt (Ollama ou données). Veuillez réessayer dans un instant."}), 503

    llm_prompt = build_llm_prompt(user_message, df_merged_data)

    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": llm_prompt,
            "stream": False,
            "keep_alive": "5m",
            "options": {"temperature": 0.0}
        }
        headers = {"Content-Type": "application/json"}

        # Removed timeout here
        response = requests.post(LLM_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        response_data = response.json()
        llm_response_text = response_data.get("response", "Erreur : Clé 'response' manquante ou inattendue dans la réponse de l'API.")

        print(f"Tokens used: Prompt={response_data.get('prompt_eval_count', 0)}, Response={response_data.get('eval_count', 0)}")

        return jsonify({"response": llm_response_text})

    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"Erreur de connexion à l'API Ollama à {OLLAMA_API_BASE_URL}. Assurez-vous qu'Ollama est en cours d'exécution et que le modèle est chargé."}), 503
    # Removed specific requests.exceptions.Timeout catch as no explicit timeout is set
    except requests.exceptions.RequestException as e:
        # This will now catch any request-related errors, including implicit timeouts if the connection is dropped
        return jsonify({"error": f"Erreur HTTP/requête avec Ollama: {e}. Vérifiez les logs Ollama."}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "La réponse d'Ollama n'était pas un JSON valide."}), 500
    except Exception as e:
        return jsonify({"error": f"Une erreur inattendue est survenue: {e}"}), 500

@app.route('/api/status', methods=['GET'])
def api_status():
    """Endpoint API pour vérifier si Ollama est prêt et les données sont chargées."""
    return jsonify({
        "ollama_ready": ollama_ready,
        "data_loaded": data_loaded
    })

# C'est cette partie qui manquait et qui provoquait l'erreur 404 !

@app.route('/api/data_summary', methods=['GET'])
def api_data_summary():
    """
    Endpoint API pour fournir un aperçu des données chargées et des top anomalies.
    """
    if df_merged_data is None or df_merged_data.empty:
        # Retourne 503 Service Unavailable si les données ne sont pas prêtes
        return jsonify({"error": "Données non chargées ou vides. Le backend est peut-être encore en cours d'initialisation."}), 503

    summary = {}
    
    # Get head of the DataFrame
    # Assurez-vous que df_merged_data n'est pas None avant d'appeler head()
    if df_merged_data is not None:
        summary['head'] = df_merged_data.head(5).to_dict(orient='records')
    else:
        summary['head'] = [] # Retourne une liste vide si le DataFrame est None

    # Get top 5 Isolation Forest anomalies
    if df_merged_data is not None and 'if_score' in df_merged_data.columns and 'if_prediction' in df_merged_data.columns:
        try:
            # Filtrer les logs prédits comme anomalies par IF (prediction == -1)
            if_anomalies = df_merged_data[df_merged_data['if_prediction'] == -1].copy()
            if not if_anomalies.empty:
                # Prendre les 5 avec le score le plus bas (le plus anormal)
                top_if_anomalies = if_anomalies.nsmallest(5, 'if_score', keep='all')
                context_data_string = "Top 5 Logs considérés comme Anormaux par Isolation Forest (avec scores et prédictions) :\n"
                cols_for_if_top = [col for col in ['original_index', 'log_text', 'if_score', 'if_prediction', 'ocsvm_score', 'ocsvm_prediction', 'severity_unified_original_x'] if col in top_if_anomalies.columns]
                summary['top_if_anomalies'] = top_if_anomalies[cols_for_if_top].to_dict(orient='records')
        except Exception as e:
            print(f"Warning: Could not get top IF anomalies for API summary: {e}")
            summary['top_if_anomalies_error'] = str(e)
    else:
        summary['top_if_anomalies'] = [] # Ou un message indiquant que les colonnes sont absentes

    # Get top 5 One-Class SVM anomalies
    if df_merged_data is not None and 'ocsvm_score' in df_merged_data.columns and 'ocsvm_prediction' in df_merged_data.columns:
        try:
            # Filtrer les logs prédits comme anomalies par OCSVM (prediction == -1)
            ocsvm_anomalies = df_merged_data[df_merged_data['ocsvm_prediction'] == -1].copy()
            if not ocsvm_anomalies.empty:
                # Prendre les 5 avec le score le plus bas (le plus anormal)
                top_ocsvm_anomalies = ocsvm_anomalies.nsmallest(5, 'ocsvm_score', keep='all')
                context_data_string = "Top 5 Logs considérés comme Anormaux par One-Class SVM (avec scores et prédictions) :\n"
                cols_for_ocsvm_top = [col for col in ['original_index', 'log_text', 'if_score', 'if_prediction', 'ocsvm_score', 'ocsvm_prediction', 'severity_unified_original_x'] if col in top_ocsvm_anomalies.columns]
                summary['top_ocsvm_anomalies'] = top_ocsvm_anomalies[cols_for_ocsvm_top].to_dict(orient='records')
        except Exception as e:
            print(f"Warning: Could not get top OCSVM anomalies for API summary: {e}")
            summary['top_ocsvm_anomalies_error'] = str(e)
    else:
        summary['top_ocsvm_anomalies'] = [] # Ou un message indiquant que les colonnes sont absentes
            
    return jsonify(summary)

@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics for this Flask application."""
    # Cette fonction génère le texte des métriques Prometheus
    # à partir du registre par défaut (REGISTRY) de prometheus_client.
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

if __name__ == '__main__':
    # Démarre l'installation d'Ollama et le chargement des données dans un thread séparé
    # C'est la solution pour remplacer @app.before_first_request dans les versions récentes de Flask.
    setup_thread = threading.Thread(target=load_data_and_set_status)
    setup_thread.daemon = True # Permet au thread de s'arrêter si le programme principal se termine
    setup_thread.start()

    # Lance l'application Flask
    app.run(host='0.0.0.0', port=8000)
