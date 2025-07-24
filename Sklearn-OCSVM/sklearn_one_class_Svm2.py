import pandas as pd
import numpy as np
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
# Assurez-vous que le fichier 'analyse_spacy.py' est dans le même répertoire
# ou que le module est correctement installé/accessible.
from analyse_spacy2 import get_log_vectors, clean
from sklearn.metrics import classification_report, confusion_matrix
import sys # Importé pour la gestion des erreurs potentielles

from flask import Flask, request, jsonify, Response # Flask est déjà importé, mais rappelé ici pour clarté
from prometheus_client import generate_latest, Counter, Histogram, Gauge, REGISTRY
import time # Pour simuler la latence si nécessaire et mesurer

# --- 1. Load & Prepare Data ---
print("Chargement et nettoyage des données...")
try:
    # Nettoyage + parsing. La fonction 'clean' doit retourner un DataFrame
    # où la dernière colonne contient les labels ('severity_unified').
    df = clean("logs.csv")
    if df.empty:
        print("Erreur : Le DataFrame est vide après le nettoyage.")
        sys.exit(1) # Arrête le script si le DataFrame est vide
    print(f"Données chargées. Shape: {df.shape}")
except FileNotFoundError:
    print("Erreur : Le fichier 'logs.csv' est introuvable.")
    sys.exit(1) # Arrête le script si le fichier n'existe pas
except Exception as e:
    print(f"Erreur lors du chargement ou nettoyage des données : {e}")
    sys.exit(1) # Arrête le script en cas d'autre erreur

# --- Découpage du data ---

# - Mettre les labels du logs dans une liste à part
# On suppose que la dernière colonne du DataFrame retourné par clean() est la colonne des labels.
try:
    # .iloc[:, -1] sélectionne la dernière colonne. .tolist() la convertit en liste.
    true_labels = df.iloc[:, -1].tolist()
    print(f"{len(true_labels)} labels extraits.")
    # Il est utile de vérifier les labels uniques pour s'assurer qu'ils correspondent à ce qu'on attend
    unique_true_labels = sorted(list(set(true_labels)))
    print(f"Labels uniques trouvés dans les données réelles : {unique_true_labels}")
    # Assurez-vous que ces labels correspondent sémantiquement à "normal" et "abnormal"
    # pour que la comparaison finale ait du sens.
except IndexError:
    print("Erreur : Impossible d'extraire la colonne de labels. Le DataFrame a-t-il assez de colonnes ?")
    sys.exit(1)
except Exception as e:
    print(f"Erreur lors de l'extraction des labels : {e}")
    sys.exit(1)

# - Le reste du data le faire une copie et le mettre dans une variable à part aussi
try:
    # .iloc[:, :-1] sélectionne toutes les colonnes SAUF la dernière.
    # .copy() crée une copie explicite pour éviter les SettingWithCopyWarning
    # et garantir que les modifications ultérieures n'affectent pas le DataFrame original 'df'.
    features_df = df.iloc[:, :-1].copy()
    print(f"DataFrame de features créé. Shape: {features_df.shape}")
    if features_df.empty:
        print("Erreur : Le DataFrame de features est vide.")
        sys.exit(1)
except Exception as e:
    print(f"Erreur lors de la création de la copie des features : {e}")
    sys.exit(1)

# --- 2. Safe Vectorization ---
# Cette étape utilise UNIQUEMENT la variable `features_df` (data sans labels)

# Définition d'une dimension de vecteur attendue (par exemple, 300 pour spaCy)
EXPECTED_VECTOR_DIM = 300

def safe_vectorize(row_data):
    """Vectorise une ligne de log en joignant ses éléments et gère les erreurs."""
    try:
        # Convertit tous les éléments de la ligne en string et les joint avec un espace
        log_text = " ".join(map(str, row_data))
        if not log_text.strip(): # Vérifie si le texte est vide ou juste des espaces
             print("Warning: Ligne de log vide rencontrée, retourne un vecteur nul.")
             return np.zeros(EXPECTED_VECTOR_DIM)

        # Appelle get_log_vectors qui doit retourner une liste de vecteurs (même pour un seul log)
        vector = get_log_vectors([log_text])[0] # Prend le premier (et unique) vecteur de la liste

        # Vérifie si le vecteur a la bonne dimension
        if vector.shape[0] != EXPECTED_VECTOR_DIM:
            print(f"Warning: Dimension de vecteur inattendue ({vector.shape[0]}) pour le log: '{log_text[:100]}...'. Retourne un vecteur nul.")
            return np.zeros(EXPECTED_VECTOR_DIM)
        return vector
    except Exception as e:
        # Affiche l'erreur et le début du log problématique pour le débogage
        log_text_preview = " ".join(map(str, row_data))[:100] # Aperçu du log
        print(f"Echec de la vectorisation pour le log : '{log_text_preview}...' - Erreur : {e}")
        # Retourne un vecteur de zéros de la dimension attendue en cas d'échec
        return np.zeros(EXPECTED_VECTOR_DIM)

print("Vectorisation des logs (utilisation des features uniquement)...")
# Applique la vectorisation sécurisée à chaque ligne du DataFrame de features
# .values retourne un NumPy array des valeurs du DataFrame, itérer dessus est efficace
log_vectors = [safe_vectorize(row) for row in features_df.values]

# Vérification post-vectorisation
if not log_vectors:
    print("Erreur : La vectorisation n'a produit aucun vecteur.")
    sys.exit(1)

# Convertit la liste de vecteurs en un array NumPy pour scikit-learn
# C'est la variable 'X' qui sera utilisée pour l'entraînement et la prédiction
X = np.array(log_vectors)
print(f"Vectorisation terminée. Shape de la matrice de vecteurs (X) : {X.shape}")

# Vérifie si la matrice X contient des NaNs ou des infinis qui peuvent poser problème
if np.isnan(X).any() or np.isinf(X).any():
    print("Warning: Des valeurs NaN ou infinies détectées dans les vecteurs après vectorisation. Le modèle pourrait échouer.")
    # Optionnel : Imputer les NaNs/Infinis si nécessaire, par exemple avec la moyenne
    # from sklearn.impute import SimpleImputer
    # imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
    # X = imputer.fit_transform(X)
    # X = np.nan_to_num(X) # Remplace NaN par 0 et inf par de grands nombres finis

# --- 3. Standardization ---
# Standardise les features (vecteurs) pour que le modèle SVM fonctionne mieux
print("Standardisation des vecteurs de features...")
scaler = StandardScaler()
# Fitte le scaler sur les données ET les transforme en une seule étape
X_scaled = scaler.fit_transform(X)
print(f"Standardisation terminée. Shape des données standardisées : {X_scaled.shape}")

# --- 4. Train One-Class SVM ---
# Entraîne le modèle sur les données standardisées SANS LABELS ('X_scaled')
print("Entraînement du modèle One-Class SVM...")
# Paramètres de OneClassSVM :
# - kernel='rbf': Kernel Gaussien (souvent un bon choix par défaut)
# - gamma: Coefficient du kernel. 'scale' (1 / (n_features * X.var())) ou 'auto' (1 / n_features) sont de bonnes options,
#          ou une valeur numérique comme 0.001 si déterminée par validation croisée.
# - nu: Borne supérieure sur la fraction d'erreurs d'entraînement et borne inférieure
#       sur la fraction de vecteurs supports. C'est aussi une estimation de la proportion d'anomalies (outliers).
#       Une valeur typique est entre 0.01 et 0.1 (ici 0.05 = 5% d'anomalies attendues).
model = OneClassSVM(kernel='rbf', gamma='scale', nu=0.1) # gamma='scale' est souvent un bon point de départ
try:
    model.fit(X_scaled)
    print("Entraînement terminé.")
except Exception as e:
    print(f"Erreur lors de l'entraînement du modèle SVM : {e}")
    sys.exit(1)

# --- 5. Predict & Map to Text Labels ---
# Fait des prédictions sur les MÊMES données que celles utilisées pour l'entraînement
# (ce qui est standard pour la détection d'anomalies non supervisée comme One-Class SVM)
print("Prédiction des labels...")
# .predict() retourne 1 pour les inliers (normaux) et -1 pour les outliers (anomalies)
y_pred_numeric = model.predict(X_scaled)

# Mappe les sorties numériques (-1, 1) vers des labels textuels ("abnormal", "normal")
# Cette étape est cruciale pour pouvoir comparer avec 'true_labels' qui sont probablement textuels.
# Assurez-vous que "abnormal" correspond à -1 (outlier) et "normal" à 1 (inlier).
y_pred_labels = ["abnormal" if p == -1 else "normal" for p in y_pred_numeric]
print("Mapping des prédictions terminé.")

# --- 6. Scientific Comparison (Revised Approach) ---
# Faire une comparaison en analysant comment les prédictions binaires
# se répartissent sur les vrais labels multi-classes.

print("\n--- Analyse de la Répartition des Prédictions SVM sur les Vrais Labels ---")

# Vérifie si le nombre de prédictions correspond au nombre de labels réels
if len(true_labels) != len(y_pred_labels):
    print(f"Erreur critique : Le nombre de labels réels ({len(true_labels)}) ne correspond pas au nombre de labels prédits ({len(y_pred_labels)}).")
    sys.exit(1) # Arrêt car la comparaison est impossible

# Labels prédits par le modèle SVM
predicted_labels_set = sorted(list(set(y_pred_labels))) # Sera ['abnormal', 'normal']
# Vrais labels uniques de vos données
true_labels_set = sorted(list(set(true_labels)))

print(f"Labels prédits par le modèle : {predicted_labels_set}")
print(f"Vrais labels trouvés dans les données : {true_labels_set}")

# Calculer la matrice de confusion entre les vrais labels multi-classes et les prédictions binaires
# Les lignes seront les vrais labels, les colonnes seront les prédictions ['abnormal', 'normal']
cm = confusion_matrix(true_labels, y_pred_labels, labels=true_labels_set + predicted_labels_set) # Assure que toutes les étiquettes sont considérées

# Extraire la sous-matrice pertinente : Lignes=Vrais Labels, Colonnes=Prédits ['abnormal', 'normal']
# Trouver les index des colonnes pour 'abnormal' et 'normal'
try:
    labels_for_cm_cols = sorted(list(set(y_pred_labels))) # Doit être ['abnormal', 'normal']
    abnormal_col_idx = labels_for_cm_cols.index('abnormal')
    normal_col_idx = labels_for_cm_cols.index('normal')
except ValueError:
    print("Erreur : Les prédictions ne contiennent pas 'abnormal' ou 'normal'. Vérifiez l'étape 5.")
    # Si par ex. seulement 'normal' est prédit, il faut ajuster
    if 'abnormal' not in labels_for_cm_cols and 'normal' in labels_for_cm_cols:
         abnormal_col_idx = -1 # Marqueur pour indiquer absence
         normal_col_idx = labels_for_cm_cols.index('normal')
    elif 'normal' not in labels_for_cm_cols and 'abnormal' in labels_for_cm_cols:
         normal_col_idx = -1
         abnormal_col_idx = labels_for_cm_cols.index('abnormal')
    else: # Aucun des deux n'est prédit? Très improbable.
         print("Erreur: Ni 'normal' ni 'abnormal' trouvés dans les prédictions.")
         sys.exit(1)


# Utiliser pandas pour une manipulation plus facile (facultatif mais pratique)
# Recalculons avec pandas pour la clarté
#cm_specific = confusion_matrix(true_labels, y_pred_labels, labels=labels_for_cm_cols) # Met les colonnes dans l'ordre ['abnormal', 'normal']
cm_df = pd.crosstab(pd.Series(true_labels, name='Vrai Label'),
                    pd.Series(y_pred_labels, name='Prédit par SVM'),
                    margins=False) # Crée un tableau croisé Vrai vs Prédit

# Assurer que les colonnes 'abnormal' et 'normal' existent, ajouter si manquantes avec des zéros
if 'abnormal' not in cm_df.columns: cm_df['abnormal'] = 0
if 'normal' not in cm_df.columns: cm_df['normal'] = 0
cm_df = cm_df[['abnormal', 'normal']] # Garde et ordonne les colonnes

print("\n--- Matrice de Confusion (Vrai Label vs Prédiction SVM) ---")
print(cm_df)

print("\n--- Analyse par Vrai Label ---")
results = []
for true_label in cm_df.index:
    count_abnormal = cm_df.loc[true_label, 'abnormal']
    count_normal = cm_df.loc[true_label, 'normal']
    total_count = count_abnormal + count_normal

    if total_count > 0:
        percent_abnormal = (count_abnormal / total_count) * 100
        percent_normal = (count_normal / total_count) * 100
    else:
        percent_abnormal = 0
        percent_normal = 0

    results.append({
        "Vrai Label": true_label,
        "Total Instances": total_count,
        "Prédit Abnormal": count_abnormal,
        "Prédit Normal": count_normal,
        "% Prédit Abnormal": round(percent_abnormal, 2),
    })

# Afficher les résultats dans un DataFrame
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False)) # .to_string pour un meilleur affichage

# Optionnel : Analyse globale des prédictions 'abnormal'
total_predicted_abnormal = results_df['Prédit Abnormal'].sum()
print(f"\nTotal d'instances prédites comme 'abnormal' par le SVM : {total_predicted_abnormal}")
if total_predicted_abnormal > 0:
    print("\nRépartition des prédictions 'abnormal' parmi les Vrais Labels:")
    abnormal_distribution = cm_df[cm_df['abnormal'] > 0]['abnormal'].sort_values(ascending=False)
    print(abnormal_distribution)
    # Vous pourriez aussi calculer le pourcentage de chaque vrai label parmi les prédictions abnormal
    # Ex: (Nombre de 'Error' prédits abnormal / Total prédits abnormal) * 100

print("\nScript terminé avec succès.")

# --- Fin de la Section 6 Modifiée ---
# Le reste du script (imports, chargement, vectorisation, training, prédiction initiale) reste identique.



# --- 7. Obtenir les scores de décision pour One-Class SVM ---
# Le score est la distance au boundary. Plus c'est négatif, plus c'est loin et donc anormal.
# prediction = sign(score). predict() fait cela pour vous (-1 ou 1).
# Nous avons besoin du score numérique pour les comparaisons dans le dashboard.
print("\nCalcul des scores de décision One-Class SVM...")
try:
    # Utilise les données standardisées qui ont été utilisées pour la prédiction
    ocsvm_decision_scores = model.decision_function(X_scaled)
    print("Scores de décision OCSVM calculés.")
except Exception as e:
    print(f"Erreur lors du calcul des scores de décision OCSVM : {e}")
    ocsvm_decision_scores = [np.nan] * len(X_scaled) # Gérer l'erreur en mettant des NaN


# --- 8. Sauvegarder les résultats pour le Dashboard ---
print("Sauvegarde des résultats One-Class SVM pour le dashboard...")

# L'index de 'features_df' correspond à l'index du DataFrame 'df' nettoyé,
# qui doit correspondre à l'index utilisé dans le script Isolation Forest.
original_indices = features_df.index

# Créez un DataFrame avec les informations nécessaires pour le dashboard
# Incluez l'index original, le score, la prédiction, et les vrais labels
results_ocsvm_df = pd.DataFrame({
    'original_index': original_indices,
    'ocsvm_score': ocsvm_decision_scores, # Score de décision One-Class SVM
    'ocsvm_prediction': y_pred_labels, # Prédiction 'normal'/'abnormal' OCSVM (chaîne)
    'severity_unified_original': true_labels, # Vrai label original (string)
    # Pour la cohérence, convertissons aussi le vrai label en binaire ici
    'severity_unified_binary': [1 if str(val).lower() in ['abnormal', 'anomaly', 'critical', 'error'] else 0
                                for val in true_labels]
})

# Définir le nom du fichier de sortie
output_filename_ocsvm = "one_class_svm_results_for_dashboard.csv"

# Sauvegarder le DataFrame en CSV
try:
    results_ocsvm_df.to_csv(output_filename_ocsvm, index=False)
    print(f"Résultats One-Class SVM sauvegardés dans {output_filename_ocsvm}")
except Exception as e:
    print(f"Erreur lors de la sauvegarde des résultats One-Class SVM : {e}")


from flask import Flask, request, jsonify

# Initialiser Flask
app = Flask(__name__)

# --- DÉFINITION DES MÉTRIQUES PROMETHEUS ---
# Compteur pour le nombre total de requêtes à l'API de prédiction One-Class SVM
OCSVM_PREDICT_REQUESTS_TOTAL = Counter(
    'ocsvm_predict_requests_total', 'Total requests to the One-Class SVM /predict endpoint'
)
# Histogramme pour la latence de l'opération de prédiction One-Class SVM
OCSVM_PREDICT_LATENCY_SECONDS = Histogram(
    'ocsvm_predict_latency_seconds', 'Latency of One-Class SVM prediction in seconds'
)
# Compteur pour le nombre d'erreurs lors de la prédiction One-Class SVM
OCSVM_PREDICT_ERRORS_TOTAL = Counter(
    'ocsvm_predict_errors_total', 'Total errors during One-Class SVM prediction'
)
# Jauge pour le nombre d'anomalies détectées lors de la dernière exécution (à mettre à jour)
OCSVM_LAST_ANOMALIES_COUNT = Gauge(
    'ocsvm_last_anomalies_count', 'Number of anomalies detected in the last One-Class SVM run'
)
# Jauge pour la proportion d'anomalies détectées lors de la dernière exécution
OCSVM_LAST_ANOMALIES_PERCENT = Gauge(
    'ocsvm_last_anomalies_percent', 'Percentage of anomalies detected in the last One-Class SVM run'
)
# Histogramme pour la durée d'entraînement du modèle One-Class SVM
OCSVM_TRAINING_LATENCY_SECONDS = Histogram(
    'ocsvm_training_latency_seconds', 'Latency of One-Class SVM model training in seconds'
)

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
        
        # Faire des prédictions avec le modèle One-Class SVM
        y_pred = model.predict(X_scaled)
        y_pred_labels = ["abnormal" if p == -1 else "normal" for p in y_pred]
        
        # Retourner les prédictions sous forme JSON
        return jsonify({"predictions": y_pred_labels})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics for this Flask application."""
    # Cette fonction génère le texte des métriques Prometheus
    # à partir du registre par défaut (REGISTRY) de prometheus_client.
    return Response(generate_latest(REGISTRY), mimetype='text/plain')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
