# app.py
import streamlit as st
import requests
import pandas as pd # Needed for displaying data, not for direct loading

# --- Configuration for Streamlit ---
# IMPORTANT: This URL should point to your Flask backend's address and port.
# If running Flask on localhost:8000, this is correct.
FLASK_BACKEND_URL = "http://localhost:8000"

# --- Nouvelle Section 8 : Chatbot d'Analyse de Logs ---
st.header("Chatbot d'Analyse de Logs")
st.write("Posez des questions au modèle LLM DeepSeek sur vos logs et les résultats d'anomalies.")

# Initialiser l'historique de la conversation dans st.session_state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "backend_status" not in st.session_state:
    st.session_state.backend_status = "Initialisation du backend..."
if "data_results" not in st.session_state:
    st.session_state.data_results = pd.DataFrame() # Initialize as empty DataFrame

# Function to fetch backend status
@st.cache_data(ttl=5) # Cache status for 5 seconds to avoid excessive calls
def get_backend_status():
    try:
        response = requests.get(f"{FLASK_BACKEND_URL}/api/status", timeout=2)
        response.raise_for_status()
        status_data = response.json()
        return status_data.get('ollama_ready', False), status_data.get('data_loaded', False)
    except requests.exceptions.ConnectionError:
        return False, False # Flask backend not reachable
    except Exception as e:
        st.error(f"Erreur lors de la récupération du statut du backend: {e}")
        return False, False

# Display backend status
ollama_ready, data_loaded = get_backend_status()

if ollama_ready and data_loaded:
    st.success("Backend (Ollama & Données) prêt ! Vous pouvez poser vos questions.")
    st.session_state.backend_status = "Prêt à chatter !"
    # Optionally, you can fetch a small sample of data if needed for display purposes
    # For now, we'll assume the context is handled by the Flask app.
elif ollama_ready and not data_loaded:
    st.warning("Ollama est prêt, mais les données sont en cours de chargement sur le backend.")
    st.session_state.backend_status = "Chargement des données..."
else:
    st.info("Initialisation du backend (Ollama et chargement des données)... Cela peut prendre plusieurs minutes.")
    st.session_state.backend_status = "Initialisation..."

# Afficher les messages précédents de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie pour le message de l'utilisateur
user_prompt = st.chat_input("Posez une question sur vos logs ou l'analyse d'anomalies...",
                             disabled=not (ollama_ready and data_loaded))

# Si l'utilisateur a tapé un message (et appuyé sur Entrée)
if user_prompt:
    # Ajouter le message de l'utilisateur à l'historique et l'afficher immédiatement
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # --- DÉBUT DU CODE POUR L'APPEL RÉEL À L'API DU MODÈLE LLM VIA FLASK ---
    with st.chat_message("assistant"):
        with st.spinner("Le modèle réfléchit..."): # Show spinner
            try:
                # Appel à l'endpoint /api/chat de l'application Flask
                response = requests.post(
                    f"{FLASK_BACKEND_URL}/api/chat",
                    json={"message": user_prompt},
                    timeout=300 # Increased timeout for potentially long LLM responses
                )
                response.raise_for_status() # Lève une exception pour les codes d'état HTTP d'erreur (4xx ou 5xx)

                llm_response_data = response.json()
                llm_response_text = llm_response_data.get("response", "Erreur : La réponse de l'API Flask ne contient pas la clé 'response' attendue.")

                # Suppression des balises <think> après réception (si le LLM les produit malgré l'instruction)
                llm_response_text = llm_response_text.replace("<think>", "").replace("</think>", "").strip()

            except requests.exceptions.ConnectionError:
                llm_response_text = f"Erreur de connexion : Impossible de se connecter au backend Flask à l'URL {FLASK_BACKEND_URL}. Est-il lancé et accessible ?"
            except requests.exceptions.Timeout:
                llm_response_text = "La requête au backend Flask a expiré. Le modèle est peut-être trop lourd ou la réponse prend trop de temps."
            except requests.exceptions.RequestException as e:
                llm_response_text = f"Erreur lors de la communication avec le backend Flask : {e}. Vérifiez les logs du backend."
            except Exception as e:
                llm_response_text = f"Une erreur inattendue est survenue : {e}"

        st.markdown(llm_response_text)
        st.session_state.messages.append({"role": "assistant", "content": llm_response_text})

# --- Pied de page (reste inchangé) ---
st.write("\n---")
st.write("Dashboard généré avec Streamlit.")
