pipeline {
    agent any

    environment {
        IMAGE_NAME     = "asx-stock-predictor"
        IMAGE_TAG      = "${BUILD_NUMBER}"
        SONAR_HOST     = "http://localhost:9000"
        STAGING_PORT   = "5001"
        PROD_PORT      = "5002"
    }

    stages {

        // ─── STAGE 1: BUILD ───────────────────────────────────────────
        stage("Build") {
            steps {
                echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
            }
            post {
                success { echo "Build artefact created: ${IMAGE_NAME}:${IMAGE_TAG}" }
            }
        }

        // ─── STAGE 2: TEST ────────────────────────────────────────────
        stage("Test") {
            steps {
                sh """
                    pip install -r requirements.txt
                    pytest tests/ -v \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing \
                        --junitxml=test-results.xml
                """
            }
            post {
                always {
                    junit "test-results.xml"
                    publishHTML([
                        allowMissing: false,
                        reportDir: ".",
                        reportFiles: "coverage.xml",
                        reportName: "Coverage Report"
                    ])
                }
            }
        }

        // ─── STAGE 3: CODE QUALITY ────────────────────────────────────
        stage("Code Quality") {
            steps {
                withSonarQubeEnv("SonarQube") {
                    sh """
                        sonar-scanner \
                          -Dsonar.projectKey=asx-stock-predictor \
                          -Dsonar.sources=app \
                          -Dsonar.tests=tests \
                          -Dsonar.python.coverage.reportPaths=coverage.xml \
                          -Dsonar.host.url=${SONAR_HOST}
                    """
                }
                timeout(time: 5, unit: "MINUTES") {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // ─── STAGE 4: SECURITY ────────────────────────────────────────
        stage("Security") {
            steps {
                sh """
                    # Scan Docker image for CVEs with Trivy
                    trivy image --exit-code 0 \
                        --severity HIGH,CRITICAL \
                        --format table \
                        --output trivy-report.txt \
                        ${IMAGE_NAME}:${IMAGE_TAG}

                    # Scan Python code with Bandit
                    pip install bandit
                    bandit -r app/ -f json -o bandit-report.json || true
                    bandit -r app/ -ll
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: "trivy-report.txt, bandit-report.json"
                }
            }
        }

        // ─── STAGE 5: DEPLOY (staging) ────────────────────────────────
        stage("Deploy") {
            steps {
                echo "Deploying to staging environment on port ${STAGING_PORT}"
                sh """
                    docker stop ${IMAGE_NAME}-staging || true
                    docker rm   ${IMAGE_NAME}-staging || true
                    docker run -d \
                        --name ${IMAGE_NAME}-staging \
                        -p ${STAGING_PORT}:5000 \
                        -e FLASK_ENV=staging \
                        ${IMAGE_NAME}:${IMAGE_TAG}
                    sleep 5
                    curl -f http://localhost:${STAGING_PORT}/health || exit 1
                """
            }
        }

        // ─── STAGE 6: RELEASE (production) ───────────────────────────
        stage("Release") {
            steps {
                echo "Promoting build ${IMAGE_TAG} to production"
                sh """
                    # Tag the image as a versioned release
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:release-${IMAGE_TAG}

                    # Stop existing prod container
                    docker stop ${IMAGE_NAME}-prod || true
                    docker rm   ${IMAGE_NAME}-prod || true

                    # Run production container
                    docker run -d \
                        --name ${IMAGE_NAME}-prod \
                        -p ${PROD_PORT}:5000 \
                        -e FLASK_ENV=production \
                        ${IMAGE_NAME}:release-${IMAGE_TAG}

                    sleep 5
                    curl -f http://localhost:${PROD_PORT}/health || exit 1
                """
                // Tag in Git for version tracking
                sh """
                    git config user.email "jenkins@ci.local"
                    git config user.name "Jenkins"
                    git tag -a v1.${IMAGE_TAG} -m "Release build ${IMAGE_TAG}" || true
                """
            }
        }

        // ─── STAGE 7: MONITORING ──────────────────────────────────────
        stage("Monitoring") {
            steps {
                sh """
                    # Start Prometheus + Grafana via compose
                    docker-compose up -d prometheus grafana

                    sleep 10

                    # Verify /metrics endpoint is live
                    curl -f http://localhost:${PROD_PORT}/metrics | grep prediction_requests_total

                    # Verify Prometheus is scraping
                    curl -s http://localhost:9090/api/v1/targets \
                        | grep -q '"health":"up"' \
                        && echo "Prometheus target healthy" \
                        || echo "Prometheus target pending"
                """
                echo "Grafana dashboard available at http://localhost:3000 (admin/admin)"
            }
        }
    }

    post {
        success {
            echo "Pipeline completed successfully — build ${IMAGE_TAG} is live."
        }
        failure {
            echo "Pipeline FAILED at stage. Check logs above."
            // Add email notification here if EmailExt plugin is installed
            // mail to: 'your@email.com', subject: "FAILED: ${JOB_NAME} #${BUILD_NUMBER}"
        }
        always {
            archiveArtifacts artifacts: "**/*.xml, **/*.txt, **/*.json", allowEmptyArchive: true
            cleanWs()
        }
    }
}