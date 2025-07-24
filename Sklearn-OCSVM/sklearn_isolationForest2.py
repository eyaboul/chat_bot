
# --- Isolation Forest Anomaly Detection (Improved Version) dali ---
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from analyse_spacy2 import get_log_vectors, clean  # Ensure this module is properly configured
from collections import Counter
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score




# --- 1. Safe Vectorization with Error Handling ---
def safe_vectorize(text):
    """Wrapper to handle potential vectorization failures"""
    try:
        return get_log_vectors([text])[0]
    except Exception as e:
        print(f"Vectorization failed for: '{text[:50]}...' - Error: {str(e)}")
        return np.zeros(300)  # Fallback: zero vector matching spaCy's typical dim

# --- 2. Load & Prepare Data ---
df = clean("logs.csv")
logs_df = pd.DataFrame(df)

# --- 3. Stocker les colonnes de labels dans une liste ---
label_columns = logs_df["severity_unified"]
logs = logs_df.iloc[:, :-1] 

# --- 5. Vectorize Logs ---
print("Vectorizing logs...")
log_vectors = [safe_vectorize(str(text)) for text in logs.values]
data = pd.DataFrame(log_vectors)

# --- 6. Train Model on Full Dataset ---
model = IsolationForest(
    n_estimators=500,
    max_samples=0.9,
    max_features=0.5,
    contamination=0.10,
    random_state=42
)
model.fit(data)

# --- 7. Predict & Analyze ---
predictions = model.predict(data)
decision_scores = model.decision_function(data)
y_pred_mapped = ['abnormal' if val == -1 else 'normal' for val in predictions]

# --- 8. Résumé ---
print(y_pred_mapped)
counter = Counter(y_pred_mapped)
print(f"Anomalies détectées: {counter['abnormal']}")
print(f"Logs normaux détectés: {counter['normal']}")

# --- 9. Comparaison avec 'severity_unified' ---
true_labels = label_columns.tolist()  # Convert Series to list
comparison = list(zip(y_pred_mapped, true_labels))

print("\nComparaison (prediction vs. vrai label):")
for i, (pred, true) in enumerate(comparison[:10]):  # afficher les 10 premiers exemples
    print(f"{i+1}. Prédit: {pred} | Réel: {true}")

# Normalize true labels (edit this mapping if your values differ)
true_binary = ['abnormal' if str(val).lower() in ['abnormal', 'anomaly', 'critical', 'error'] else 'normal'
               for val in true_labels]
         
# Convert labels to binary: 1 = abnormal, 0 = normal
y_true = [1 if label == 'abnormal' else 0 for label in true_binary]
y_pred = [1 if pred == 'abnormal' else 0 for pred in y_pred_mapped]

# Print metrics
print("\n--- Évaluation du Modèle ---")
print(confusion_matrix(y_true, y_pred))
print(classification_report(y_true, y_pred, target_names=['Normal', 'Anomalie']))

# Optional: ROC-AUC based on decision function
roc_auc = roc_auc_score(y_true, -decision_scores)  # Use negative scores, since lower = more anomalous
print(f"ROC-AUC: {roc_auc:.4f}")


# --- 10. Sauvegarder les résultats pour le Dashboard ---
print("\nSauvegarde des résultats Isolation Forest pour le dashboard...")

# Assurez-vous que 'logs_df' contient l'index original correct
# Si vous avez manipulé l'index de 'data', il vaut mieux utiliser l'index de 'logs_df'
# car il correspond au DataFrame nettoyé avant vectorisation.
original_indices = logs_df.index

# Créez un DataFrame avec les informations nécessaires pour le dashboard
# Incluez l'index original, le score, la prédiction, et les vrais labels (utiles pour la comparaison dans le dash)
results_if_df = pd.DataFrame({
    'original_index': original_indices,
    'if_score': decision_scores, # Score de décision Isolation Forest
    'if_prediction': y_pred_mapped, # Prédiction 'normal'/'abnormal' IF
    'severity_unified_original': label_columns.tolist(), # Vrai label original (string)
    'severity_unified_binary': y_true # Vrai label binaire (0/1) - déjà calculé
})

# Définir le nom du fichier de sortie
output_filename_if = "isolation_forest_results_for_dashboard.csv"

# Sauvegarder le DataFrame en CSV
try:
    results_if_df.to_csv(output_filename_if, index=False)
    print(f"Résultats Isolation Forest sauvegardés dans {output_filename_if}")
except Exception as e:
    print(f"Erreur lors de la sauvegarde des résultats Isolation Forest : {e}")

from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route('/predict', methods=['POST'])
def predict():
    # Récupérer les données envoyées par le client
    data = request.json
    logs_file = data.get("logs.csv", None)  # Nom du fichier CSV contenant les logs
    
    if not logs_file:
        return jsonify({"error": "No logs file provided"}), 400
    
    try:
        # Appeler votre fonction clean() avec le fichier CSV
        df = clean(logs.csv)
        
        # Extraire les vecteurs pour chaque log
        log_vectors = [safe_vectorize(row) for row in df.iloc[:, :-1].values]
        X = np.array(log_vectors)
        
        # Standardiser les données
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Faire des prédictions avec le modèle Isolation Forest
        y_pred = model.predict(X_scaled)
        y_pred_labels = ["abnormal" if p == -1 else "normal" for p in y_pred]
        
        # Retourner les prédictions sous forme JSON
        return jsonify({"predictions": y_pred_labels})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
