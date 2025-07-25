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
                branch 'main'
            }
            steps {
                script {
                    echo "🚀 Déploiement sur Kubernetes..."
                    
                    withCredentials([string(credentialsId: 'kubernetes-token', variable: 'K8S_TOKEN')]) {
                        // Configuration kubectl
                        sh '''
                            kubectl config set-cluster k8s-cluster --server=https://kubernetes.default.svc --insecure-skip-tls-verify=true
                            kubectl config set-credentials jenkins-user --token=$K8S_TOKEN
                            kubectl config set-context jenkins-context --cluster=k8s-cluster --user=jenkins-user --namespace=${K8S_NAMESPACE}
                            kubectl config use-context jenkins-context
                        '''
                        
                        // Vérifier la connectivité
                        sh 'kubectl cluster-info'
                        
                        // Créer le namespace si nécessaire
                        sh 'kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -'
                        
                        // Appliquer tous les manifests Kubernetes
                        sh 'kubectl apply -f k8s/'
                        
                        // Mettre à jour les images dans les déploiements
                        sh '''
                            kubectl set image deployment/spacy-service spacy-service=${DOCKER_HUB_REPO}:spacy-service-latest -n ${K8S_NAMESPACE}
                            kubectl set image deployment/sklearn-if-service sklearn-if-service=${DOCKER_HUB_REPO}:sklearn-if-service-latest -n ${K8S_NAMESPACE}
                            kubectl set image deployment/sklearn-ocsvm-service sklearn-ocsvm-service=${DOCKER_HUB_REPO}:sklearn-ocsvm-service-latest -n ${K8S_NAMESPACE}
                            kubectl set image deployment/chatbot-web chatbot-web=${DOCKER_HUB_REPO}:chatbot-web-latest -n ${K8S_NAMESPACE}
                        '''
                        
                        // Forcer le redémarrage pour puller les nouvelles images
                        sh '''
                            kubectl rollout restart deployment/spacy-service -n ${K8S_NAMESPACE}
                            kubectl rollout restart deployment/sklearn-if-service -n ${K8S_NAMESPACE}
                            kubectl rollout restart deployment/sklearn-ocsvm-service -n ${K8S_NAMESPACE}
                            kubectl rollout restart deployment/chatbot-web -n ${K8S_NAMESPACE}
                        '''
                        
                        // Attendre que les déploiements soient prêts
                        sh '''
                            kubectl rollout status deployment/spacy-service -n ${K8S_NAMESPACE} --timeout=300s
                            kubectl rollout status deployment/sklearn-if-service -n ${K8S_NAMESPACE} --timeout=300s
                            kubectl rollout status deployment/sklearn-ocsvm-service -n ${K8S_NAMESPACE} --timeout=300s
                            kubectl rollout status deployment/chatbot-web -n ${K8S_NAMESPACE} --timeout=300s
                        '''
                    }
                }
            }
        }
        
        stage('Health Check') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo "🏥 Vérification de santé des services..."
                    
                    withCredentials([string(credentialsId: 'kubernetes-token', variable: 'K8S_TOKEN')]) {
                        sh '''
                            echo "📊 État des pods:"
                            kubectl get pods -n ${K8S_NAMESPACE}
                            
                            echo "📊 État des services:"
                            kubectl get services -n ${K8S_NAMESPACE}
                            
                            # Vérifier que tous les pods sont ready
                            kubectl wait --for=condition=ready pod --all -n ${K8S_NAMESPACE} --timeout=300s
                            
                            echo "✅ Tous les services sont opérationnels!"
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
                if (env.BRANCH_NAME == 'main') {
                    echo """
                    ✅ DÉPLOIEMENT RÉUSSI!
                    
                    🎯 Branche: ${env.BRANCH_NAME}
                    📦 Build: ${env.BUILD_NUMBER}
                    🏷️ Images: ${BRANCH_NAME_CLEAN}-${BUILD_TIMESTAMP}
                    
                    🔗 Services disponibles:
                    • kubectl port-forward service/chatbot-web 8000:8000 -n ${K8S_NAMESPACE}
                    • kubectl port-forward service/prometheus 9090:9090 -n ${K8S_NAMESPACE}
                    • kubectl port-forward service/grafana 3000:3000 -n ${K8S_NAMESPACE}
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
