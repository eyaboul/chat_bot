pipeline {
    agent any

    environment {
        DOCKER_HUB_REPO = 'eyaboulaaba/pfe'
        BUILD_TIMESTAMP = "${new Date().format('yyyyMMdd-HHmmss')}"
        BRANCH_NAME_CLEAN = "${env.BRANCH_NAME.replaceAll('/', '-')}"
        K8S_NAMESPACE = 'pfe-app'
    }
    
    stages {
        stage('Checkout & Info') {
            steps {
                script {
                    echo "🔄 Pipeline déclenché pour la branche: ${env.BRANCH_NAME}"
                    echo "📦 Build Number: ${env.BUILD_NUMBER}"
                    echo "🏷️ Tag de build: ${BRANCH_NAME_CLEAN}-${BUILD_TIMESTAMP}"
                }
            }
        }
        
        stage('Build & Push Images') {
            steps {
                script {
                    def services = [
                        'spacy-service': 'Spacy',
                        'sklearn-ocsvm-service': 'Sklearn-OCSVM',
                        'sklearn-if-service': 'Sklearn-IF',
                        'chatbot-web-service': 'model_LLM'  // ✅ AJOUTER CETTE LIGNE
                    ]

                    withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
                        
                        services.each { serviceName, servicePath ->
                            def timestampTag = "${DOCKER_HUB_REPO}:${serviceName}-${BRANCH_NAME_CLEAN}-${BUILD_TIMESTAMP}"
                            def latestTag = "${DOCKER_HUB_REPO}:${serviceName}-latest"
                            
                            echo "🏗️ Building: ${timestampTag} from ${servicePath}"
                            
                            // Build
                            sh "docker build -t ${timestampTag} ./${servicePath}"
                            
                            // Login avant chaque push
                            sh 'echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin'

                            // Fonction retry pour push
                            def retryPush = { imageTag ->
                                int maxRetries = 3
                                int attempt = 0
                                boolean pushed = false
                                while (!pushed && attempt < maxRetries) {
                                    attempt++
                                    try {
                                        sh "docker push ${imageTag}"
                                        pushed = true
                                    } catch (Exception e) {
                                        echo "⚠️ Push failed for ${imageTag}, attempt ${attempt} of ${maxRetries}"
                                        if (attempt == maxRetries) {
                                            error "❌ Push failed after ${maxRetries} attempts for ${imageTag}"
                                        }
                                        sleep 10
                                    }
                                }
                            }
                            
                            retryPush(timestampTag)
                            
                            // Tag latest
                            sh "docker tag ${timestampTag} ${latestTag}"
                            
                            // Re-login pour le deuxième push
                            sh 'echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin'
                            
                            retryPush(latestTag)
                            
                            echo "✅ ${serviceName} completed"
                        }
                        
                        sh "docker logout"
                    }
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            when {
                branch 'master'  // Changez 'main' en 'master'
            }
            steps {
                script {
                    echo "🚀 Déploiement sur Kubernetes (Docker Desktop)..."
                    
                    withCredentials([string(credentialsId: 'kubernetes-token', variable: 'K8S_TOKEN')]) {
                        // Configuration kubectl pour Docker Desktop
                        sh '''
                            kubectl config set-cluster docker-desktop --server=https://kubernetes.docker.internal:6443 --insecure-skip-tls-verify=true
                            kubectl config set-credentials jenkins-user --token=$K8S_TOKEN
                            kubectl config set-context jenkins-context --cluster=docker-desktop --user=jenkins-user --namespace=${K8S_NAMESPACE}
                            kubectl config use-context jenkins-context
                        '''
                        
                        // Vérifier la connectivité
                        sh '''
                            echo "🔍 Test de connexion au cluster Docker Desktop..."
                            kubectl cluster-info
                            kubectl get nodes
                        '''
                        
                        // Créer le namespace si nécessaire
                        sh 'kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -'
                        
                        // Déployer les services (créer des déploiements basiques si pas de dossier k8s/)
                        sh '''
                            if [ -d "k8s" ]; then
                                echo "📦 Déploiement des manifests Kubernetes..."
                                
                                # Appliquer SEULEMENT les fichiers dans k8s/ racine (pas le sous-dossier monitoring)
                                for file in k8s/*.yaml k8s/*.yml; do
                                    if [ -f "$file" ]; then
                                        # Exclure les fichiers de monitoring
                                        if [[ ! "$file" =~ "monitoring" ]] && [[ ! "$file" =~ "grafana" ]] && [[ ! "$file" =~ "prometheus" ]]; then
                                            echo "Applying: $file"
                                            kubectl apply -f "$file" -n ${K8S_NAMESPACE} || echo "⚠️ Failed to apply $file"
                                        fi
                                    fi
                                done
                                
                            else
                                echo "⚠️ Dossier k8s/ non trouvé - création manuelle des services..."
                                
                                # Spacy Service
                                kubectl create deployment spacy-service --image=${DOCKER_HUB_REPO}:spacy-service-latest -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment spacy-service --port=5003 --target-port=5003 -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                
                                # Sklearn-IF Service  
                                kubectl create deployment sklearn-if-service --image=${DOCKER_HUB_REPO}:sklearn-if-service-latest -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment sklearn-if-service --port=5001 --target-port=5001 -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                
                                # Sklearn-OCSVM Service
                                kubectl create deployment sklearn-ocsvm-service --image=${DOCKER_HUB_REPO}:sklearn-ocsvm-service-latest -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment sklearn-ocsvm-service --port=5002 --target-port=5002 -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                
                                # Chatbot-Web Service (CORRIGER LE PORT)
                                kubectl create deployment chatbot-web-service --image=${DOCKER_HUB_REPO}:chatbot-web-service-latest -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment chatbot-web-service --port=8000 --target-port=8000 -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                            fi
                        '''
                        
                        // Mettre à jour les images
                        sh '''
                            echo "🔄 Mise à jour des images..."
                            kubectl set image deployment/spacy-service spacy-service=${DOCKER_HUB_REPO}:spacy-service-latest -n ${K8S_NAMESPACE} || echo "Deployment spacy-service non trouvé"
                            kubectl set image deployment/sklearn-ocsvm-service sklearn-ocsvm-service=${DOCKER_HUB_REPO}:sklearn-ocsvm-service-latest -n ${K8S_NAMESPACE} || echo "Deployment sklearn-ocsvm-service non trouvé"
                            kubectl set image deployment/sklearn-if-service sklearn-if-service=${DOCKER_HUB_REPO}:sklearn-if-service-latest -n ${K8S_NAMESPACE} || echo "Deployment sklearn-if-service non trouvé"
                            kubectl set image deployment/chatbot-web-service chatbot-web-service=${DOCKER_HUB_REPO}:chatbot-web-service-latest -n ${K8S_NAMESPACE} || echo "Deployment chatbot-web-service non trouvé"
                        '''
                        
                        // Attendre le déploiement
                        sh '''
                            echo "⏳ Attente du déploiement..."
                            kubectl rollout status deployment/spacy-service -n ${K8S_NAMESPACE} --timeout=300s || true
                            kubectl rollout status deployment/sklearn-ocsvm-service -n ${K8S_NAMESPACE} --timeout=300s || true
                            kubectl rollout status deployment/chatbot-web-service -n ${K8S_NAMESPACE} --timeout=300s || true
                        '''
                    }
                }
            }
        }
        
        stage('Health Check') {
            when {
                branch 'master'  // Changez 'main' en 'master'
            }
            steps {
                script {
                    echo "🏥 Vérification de santé des services..."
                    
                    withCredentials([string(credentialsId: 'kubernetes-token', variable: 'K8S_TOKEN')]) {
                        sh '''
                            # Reconfigurer kubectl
                            kubectl config set-cluster docker-desktop --server=https://kubernetes.docker.internal:6443 --insecure-skip-tls-verify=true
                            kubectl config set-credentials jenkins-user --token=$K8S_TOKEN
                            kubectl config set-context jenkins-context --cluster=docker-desktop --user=jenkins-user --namespace=${K8S_NAMESPACE}
                            kubectl config use-context jenkins-context
                            
                            echo "📊 État des pods:"
                            kubectl get pods -n ${K8S_NAMESPACE}
                            
                            echo "📊 État des services:"
                            kubectl get services -n ${K8S_NAMESPACE}
                            
                            echo "✅ Vérification terminée!"
                        '''
                    }
                }
            }
        }
        
        stage('Deploy Monitoring Stack') {
            when {
                branch 'master'
            }
            steps {
                script {
                    echo "📊 Déploiement de la stack de monitoring..."
                    
                    withCredentials([string(credentialsId: 'kubernetes-token', variable: 'K8S_TOKEN')]) {
                        sh '''
                            # Configuration kubectl
                            kubectl config set-cluster docker-desktop --server=https://kubernetes.docker.internal:6443 --insecure-skip-tls-verify=true
                            kubectl config set-credentials jenkins-user --token=$K8S_TOKEN
                            kubectl config set-context jenkins-context --cluster=docker-desktop --user=jenkins-user
                            kubectl config use-context jenkins-context
                            
                            # Créer le namespace monitoring
                            kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
                            
                            # Déployer les manifests de monitoring depuis le dossier k8s/monitoring/
                            if [ -d "k8s/monitoring" ]; then
                                echo "📊 Déploiement des manifests de monitoring..."
                                
                                # Appliquer tous les fichiers du dossier monitoring
                                kubectl apply -f k8s/monitoring/ -n monitoring || echo "⚠️ Erreur lors du déploiement monitoring"
                                
                                # Redémarrer Prometheus pour charger la nouvelle config
                                kubectl rollout restart deployment/prometheus -n monitoring || echo "Prometheus deployment not found"
                                
                                # Attendre que Prometheus soit prêt
                                kubectl rollout status deployment/prometheus -n monitoring --timeout=60s || echo "Prometheus rollout timeout"
                                
                                echo "📊 Vérification du déploiement monitoring..."
                                kubectl get pods -n monitoring || true
                                kubectl get services -n monitoring || true
                                
                            else
                                echo "⚠️ Dossier k8s/monitoring/ non trouvé - création manuelle..."
                                
                                # Créer Grafana manuellement
                                kubectl create deployment grafana --image=grafana/grafana:latest -n monitoring --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment grafana --port=3000 --target-port=3000 --type=NodePort -n monitoring --dry-run=client -o yaml | kubectl apply -f -
                                
                                # Créer Prometheus manuellement  
                                kubectl create deployment prometheus --image=prom/prometheus:latest -n monitoring --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment prometheus --port=9090 --target-port=9090 --type=NodePort -n monitoring --dry-run=client -o yaml | kubectl apply -f -
                            fi
                            
                            echo "📊 Stack de monitoring déployée!"
                            echo "🔗 Grafana: kubectl port-forward service/grafana 3000:3000 -n monitoring"
                            echo "🔗 Prometheus: kubectl port-forward service/prometheus 9090:9090 -n monitoring"
                        '''
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "🧹 Nettoyage..."
                sh '''
                    docker system prune -f || true
                    docker logout || true
                '''
            }
        }
        
        success {
            script {
                if (env.BRANCH_NAME == 'master') {
                    echo """
                    ✅ DÉPLOIEMENT RÉUSSI!
                    
                    🎯 Branche: ${env.BRANCH_NAME}
                    📦 Build: ${env.BUILD_NUMBER}
                    🏷️ Images: ${BRANCH_NAME_CLEAN}-${BUILD_TIMESTAMP}
                    
                    🔗 Services disponibles:
                    • kubectl port-forward service/spacy-service 5003:5003 -n ${K8S_NAMESPACE}
                    • kubectl port-forward service/sklearn-ocsvm-service 5002:5002 -n ${K8S_NAMESPACE}
                    • kubectl port-forward service/sklearn-if-service 5001:5001 -n ${K8S_NAMESPACE}
                    • kubectl port-forward service/chatbot-web-service 8000:8000 -n ${K8S_NAMESPACE}

                    💡 Pour accéder aux services:
                    • Spacy: http://localhost:5003
                    • Sklearn-OCSVM: http://localhost:5002
                    • Sklearn-IF: http://localhost:5001
                    • Chatbot: http://localhost:8000
                    
                    📊 Monitoring disponible:
                    • kubectl port-forward service/grafana 3000:3000 -n monitoring
                    • kubectl port-forward service/prometheus 9090:9090 -n monitoring
                    """
                }
            }
        }
        
        failure {
            script {
                echo """
                ❌ PIPELINE ÉCHOUÉ!
                
                🎯 Branche: ${env.BRANCH_NAME}
                📦 Build: ${env.BUILD_NUMBER}
                
                Vérifiez les logs pour identifier le problème.
                """
            }
        }
    }
}
