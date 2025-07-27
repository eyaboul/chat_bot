# pfe-project

## Overview
This project is designed to deploy machine learning services using Docker and Kubernetes. It includes services for Spacy, Sklearn OCSVM, Sklearn IF, and a Chatbot web service. Additionally, it incorporates monitoring capabilities using Prometheus and Grafana.

## Project Structure
- **docker-compose.yml**: Defines the services, networks, and volumes for the Docker containers.
- **monitoring/**: Contains configuration and data for monitoring services.
  - **grafana/**: Holds Grafana dashboards and configuration.
    - **dashboards/**: Directory for storing Grafana dashboard JSON files.
  - **prometheus/**: Contains data and configuration for Prometheus.
    - **data/**: Directory for storing Prometheus data.
  - **config/**: Configuration files for Grafana and Prometheus.
    - **grafana.ini**: Configuration settings for Grafana.
    - **prometheus.yml**: Configuration file for Prometheus.
- **services/**: Contains the code and Dockerfiles for each machine learning service.
  - **spacy-service/**
  - **sklearn-ocsvm-service/**
  - **sklearn-if-service/**
  - **chatbot-web-service/**
- **k8s/**: Contains Kubernetes manifests for deploying services and monitoring.
  - **monitoring/**
  - **manifests/**
- **Jenkinsfile**: Defines the CI/CD pipeline for building, testing, and deploying the application.

## Setup Instructions
1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd pfe-project
   ```

2. **Build and run the services**:
   ```
   docker-compose up --build
   ```

3. **Access the services**:
   - Spacy: http://localhost:5003
   - Sklearn-OCSVM: http://localhost:5002
   - Sklearn-IF: http://localhost:5001
   - Chatbot: http://localhost:8000

4. **Access Grafana**:
   - Grafana: http://localhost:3000
   - Default credentials: admin/admin

5. **Access Prometheus**:
   - Prometheus: http://localhost:9090

## Data Persistence
- **Grafana**: The dashboards are stored in the `monitoring/grafana/dashboards` directory, which is mounted as a volume in the `docker-compose.yml` to ensure they are preserved.
- **Prometheus**: The collected metrics are stored in the `monitoring/prometheus/data` directory, which is also mounted as a volume to retain data across container restarts.

## CI/CD
The project uses Jenkins for continuous integration and deployment. The `Jenkinsfile` defines the pipeline stages for building, testing, and deploying the application.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.