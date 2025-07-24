#!/bin/bash

echo "Déploiement de l'application PFE sur Kubernetes avec images Docker Hub..."

# 1. Créer le namespace
echo "Création du namespace..."
kubectl apply -f namespace.yaml

# 2. Créer le PVC pour Ollama
echo "Création du PVC pour Ollama..."
kubectl apply -f pvc-ollama-data.yaml

# 3. Déployer Ollama d'abord (nécessaire pour les autres services)
echo "Déploiement d'Ollama..."
kubectl apply -f deployment-ollama.yaml

# 4. Attendre qu'Ollama soit prêt
echo "Attente du démarrage d'Ollama..."
kubectl wait --for=condition=available --timeout=300s deployment/ollama-service -n pfe-app

# 5. Initialiser le modèle Ollama
echo "Initialisation du modèle Ollama..."
kubectl apply -f job-ollama-init.yaml

# 6. Attendre que le job se termine
echo "Attente de la fin du téléchargement du modèle..."
kubectl wait --for=condition=complete --timeout=600s job/ollama-model-init -n pfe-app

# 7. Déployer les services de base avec images Docker Hub
echo "Déploiement des services de base..."
kubectl apply -f deployment-spacy.yaml
kubectl apply -f deployment-sklearn-if.yaml
kubectl apply -f deployment-sklearn-ocsvm.yaml

# 8. Attendre que les services de base soient prêts
echo "Attente des services de base..."
kubectl wait --for=condition=available --timeout=300s deployment/spacy-service -n pfe-app
kubectl wait --for=condition=available --timeout=300s deployment/sklearn-if-service -n pfe-app
kubectl wait --for=condition=available --timeout=300s deployment/sklearn-ocsvm-service -n pfe-app

# 9. Déployer le chatbot
echo "Déploiement du chatbot..."
kubectl apply -f deployment-chatbot-web.yaml

# 10. Déployer monitoring
echo "Déploiement du monitoring..."
kubectl apply -f configmap-prometheus.yaml
kubectl apply -f deployment-prometheus.yaml
kubectl apply -f deployment-grafana.yaml

echo "Déploiement terminé!"
echo ""
echo "Vérifiez les pods avec:"
echo "kubectl get pods -n pfe-app"
echo ""
echo "Accès aux services:"
echo "kubectl port-forward service/chatbot-web 8000:8000 -n pfe-app"
echo "kubectl port-forward service/prometheus 9090:9090 -n pfe-app"
echo "kubectl port-forward service/grafana 3000:3000 -n pfe-app"