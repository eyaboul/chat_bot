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
                        'sklearn-ocsvm-service': 'Sklearn-OCSVM'
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
                            
                            // Push timestamp version
                            sh "docker push ${timestampTag}"
                            
                            // Tag latest
                            sh "docker tag ${timestampTag} ${latestTag}"
                            
                            // Re-login pour le deuxième push
                            sh 'echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin'
                            
                            // Push latest
                            sh "docker push ${latestTag}"
                            
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
                                kubectl apply -f k8s/ -n ${K8S_NAMESPACE}
                            else
                                echo "⚠️ Dossier k8s/ non trouvé - création des ressources de base..."
                                
                                # Spacy Service
                                kubectl create deployment spacy-service --image=${DOCKER_HUB_REPO}:spacy-service-latest -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment spacy-service --port=5003 --target-port=5003 -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                
                                # Sklearn-OCSVM Service
                                kubectl create deployment sklearn-ocsvm-service --image=${DOCKER_HUB_REPO}:sklearn-ocsvm-service-latest -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                                kubectl expose deployment sklearn-ocsvm-service --port=5002 --target-port=5002 -n ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                            fi
                        '''
                        
                        // Mettre à jour les images
                        sh '''
                            echo "🔄 Mise à jour des images..."
                            kubectl set image deployment/spacy-service spacy-service=${DOCKER_HUB_REPO}:spacy-service-latest -n ${K8S_NAMESPACE} || echo "Deployment spacy-service non trouvé"
                            kubectl set image deployment/sklearn-ocsvm-service sklearn-ocsvm-service=${DOCKER_HUB_REPO}:sklearn-ocsvm-service-latest -n ${K8S_NAMESPACE} || echo "Deployment sklearn-ocsvm-service non trouvé"
                        '''
                        
                        // Attendre le déploiement
                        sh '''
                            echo "⏳ Attente du déploiement..."
                            kubectl rollout status deployment/spacy-service -n ${K8S_NAMESPACE} --timeout=300s || true
                            kubectl rollout status deployment/sklearn-ocsvm-service -n ${K8S_NAMESPACE} --timeout=300s || true
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
                if (env.BRANCH_NAME == 'master') {  // Changez 'main' en 'master'
                    echo """
                    ✅ DÉPLOIEMENT RÉUSSI!
                    
                    🎯 Branche: ${env.BRANCH_NAME}
                    📦 Build: ${env.BUILD_NUMBER}
                    🏷️ Images: ${BRANCH_NAME_CLEAN}-${BUILD_TIMESTAMP}
                    
                    🔗 Services disponibles:
                    • kubectl port-forward service/spacy-service 5003:5003 -n ${K8S_NAMESPACE}
                    • kubectl port-forward service/sklearn-ocsvm-service 5002:5002 -n ${K8S_NAMESPACE}
                    
                    💡 Pour accéder aux services:
                    • Spacy: http://localhost:5003
                    • Sklearn-OCSVM: http://localhost:5002
                    """
                } else {
                    echo "✅ Build réussi pour la branche: ${env.BRANCH_NAME}"
                }
            }
        }
        
        failure {
            echo """
            ❌ PIPELINE ÉCHOUÉ!
            
            🎯 Branche: ${env.BRANCH_NAME}
            📦 Build: ${env.BUILD_NUMBER}
            
            Vérifiez les logs pour identifier le problème.
            """
        }
    }
}
