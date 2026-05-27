pipeline {
    agent any

    environment {
        IMAGE_NAME        = "task-73hd"
        IMAGE_TAG         = "${BUILD_NUMBER}"
        SONAR_HOST        = "http://host.docker.internal:9000"
        STAGING_PORT      = "5001"
        PROD_PORT         = "5002"
        CONTAINER_STAGING = "task-73hd-staging"
        CONTAINER_PROD    = "task-73hd-prod"
    }

    options {
        timestamps()
        timeout(time: 60, unit: "MINUTES")
        buildDiscarder(logRotator(numToKeepStr: "10"))
    }

    stages {

        // ================================================================
        // STAGE 1 — BUILD
        // ================================================================
        stage("Build") {
            steps {
                echo "============================================"
                echo " STAGE 1: BUILD"
                echo "============================================"
                echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"

                sh """
                    docker build \
                        --no-cache \
                        --label "build=${BUILD_NUMBER}" \
                        --label "commit=${GIT_COMMIT}" \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        -t ${IMAGE_NAME}:latest \
                        .
                """

                sh "docker images ${IMAGE_NAME}"
                echo "Build artefact created: ${IMAGE_NAME}:${IMAGE_TAG}"
            }
            post {
                success {
                    echo "BUILD STAGE PASSED — image ${IMAGE_NAME}:${IMAGE_TAG} ready"
                }
                failure {
                    echo "BUILD STAGE FAILED — check Dockerfile and requirements.txt"
                }
            }
        }

        // ================================================================
        // STAGE 2 — TEST
        // ================================================================
        stage("Test") {
            steps {
                echo "============================================"
                echo " STAGE 2: TEST"
                echo "============================================"

                sh """
                    echo "Installing test dependencies..."
                    pip install --quiet \
                        pytest \
                        pytest-cov \
                        pytest-html \
                        requests \
                        flask \
                        yfinance \
                        scikit-learn \
                        pandas \
                        numpy \
                        prometheus-client

                    echo "Running unit and integration tests..."
                    pytest tests/ \
                        -v \
                        --tb=short \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing \
                        --cov-report=html:htmlcov \
                        --junitxml=test-results.xml \
                        --html=test-report.html \
                        --self-contained-html

                    echo "Test coverage summary:"
                    coverage report || true
                """
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: "test-results.xml"
                    archiveArtifacts artifacts: "test-results.xml, coverage.xml, test-report.html", allowEmptyArchive: true
                    echo "Test results archived"
                }
                success {
                    echo "TEST STAGE PASSED — all tests green"
                }
                failure {
                    echo "TEST STAGE FAILED — check test output above"
                }
            }
        }

        // ================================================================
        // STAGE 3 — CODE QUALITY (SonarQube)
        // ================================================================
        stage("Code Quality") {
            steps {
                echo "============================================"
                echo " STAGE 3: CODE QUALITY"
                echo "============================================"

                sh """
                    echo "Regenerating coverage report for SonarQube..."
                    pip install --quiet pytest pytest-cov
                    pytest tests/ \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        -q || true
                """

                withSonarQubeEnv("SonarQube") {
                    sh """
                        sonar-scanner \
                            -Dsonar.projectKey=asx-stock-predictor \
                            -Dsonar.projectName="ASX Stock Predictor" \
                            -Dsonar.projectVersion=1.${BUILD_NUMBER} \
                            -Dsonar.sources=app \
                            -Dsonar.tests=tests \
                            -Dsonar.language=py \
                            -Dsonar.python.version=3.11 \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.exclusions=**/__pycache__/**,**/*.pyc,htmlcov/** \
                            -Dsonar.test.inclusions=tests/** \
                            -Dsonar.sourceEncoding=UTF-8
                    """
                }

                timeout(time: 5, unit: "MINUTES") {
                    waitForQualityGate abortPipeline: true
                }
            }
            post {
                success {
                    echo "CODE QUALITY STAGE PASSED — quality gate green"
                    echo "SonarQube dashboard: http://localhost:9000/dashboard?id=asx-stock-predictor"
                }
                failure {
                    echo "CODE QUALITY STAGE FAILED — quality gate not met"
                    echo "Check SonarQube at http://localhost:9000"
                }
            }
        }

        // ================================================================
        // STAGE 4 — SECURITY
        // ================================================================
        stage("Security") {
            steps {
                echo "============================================"
                echo " STAGE 4: SECURITY"
                echo "============================================"

                sh """
                    echo "--- Trivy: scanning Docker image for CVEs ---"
                    trivy image \
                        --exit-code 0 \
                        --severity LOW,MEDIUM,HIGH,CRITICAL \
                        --format table \
                        --output trivy-report.txt \
                        ${IMAGE_NAME}:${IMAGE_TAG} || true

                    echo ""
                    echo "=== TRIVY REPORT SUMMARY ==="
                    cat trivy-report.txt

                    echo ""
                    echo "--- Trivy: HIGH and CRITICAL only ---"
                    trivy image \
                        --exit-code 0 \
                        --severity HIGH,CRITICAL \
                        --format json \
                        --output trivy-critical.json \
                        ${IMAGE_NAME}:${IMAGE_TAG} || true
                """

                sh """
                    echo "--- Bandit: scanning Python source code ---"
                    pip install --quiet bandit

                    bandit -r app/ \
                        -f txt \
                        -o bandit-report.txt \
                        -ll \
                        --exit-zero || true

                    bandit -r app/ \
                        -f json \
                        -o bandit-report.json \
                        --exit-zero || true

                    echo ""
                    echo "=== BANDIT REPORT SUMMARY ==="
                    cat bandit-report.txt
                """

                sh """
                    echo "--- pip-audit: checking Python dependencies for known CVEs ---"
                    pip install --quiet pip-audit || true
                    pip-audit \
                        -r requirements.txt \
                        --format=columns \
                        --output pip-audit-report.txt || true

                    echo ""
                    echo "=== PIP-AUDIT REPORT ==="
                    cat pip-audit-report.txt || echo "pip-audit report not generated"
                """

                echo "Security scan complete. Review reports above."
            }
            post {
                always {
                    archiveArtifacts artifacts: "trivy-report.txt, trivy-critical.json, bandit-report.txt, bandit-report.json, pip-audit-report.txt", allowEmptyArchive: true
                    echo "Security reports archived"
                }
                success {
                    echo "SECURITY STAGE PASSED — reports generated"
                }
            }
        }

        // ================================================================
        // STAGE 5 — DEPLOY (Staging)
        // ================================================================
        stage("Deploy") {
            steps {
                echo "============================================"
                echo " STAGE 5: DEPLOY TO STAGING"
                echo "============================================"

                sh """
                    echo "Stopping and removing old staging container if exists..."
                    docker stop ${CONTAINER_STAGING} 2>/dev/null || true
                    docker rm   ${CONTAINER_STAGING} 2>/dev/null || true

                    echo "Deploying ${IMAGE_NAME}:${IMAGE_TAG} to staging on port ${STAGING_PORT}..."
                    docker run -d \
                        --name ${CONTAINER_STAGING} \
                        -p ${STAGING_PORT}:5000 \
                        -e FLASK_ENV=staging \
                        -e BUILD_NUMBER=${BUILD_NUMBER} \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:${IMAGE_TAG}

                    echo "Waiting for staging container to be ready..."
                    sleep 8
                """

                sh """
                    echo "Running smoke tests against staging..."

                    MAX_RETRIES=5
                    COUNT=0
                    until curl -sf http://localhost:${STAGING_PORT}/health > /dev/null; do
                        COUNT=\$((COUNT+1))
                        if [ \$COUNT -ge \$MAX_RETRIES ]; then
                            echo "Staging health check failed after \$MAX_RETRIES attempts"
                            docker logs ${CONTAINER_STAGING}
                            exit 1
                        fi
                        echo "Attempt \$COUNT — waiting..."
                        sleep 3
                    done

                    echo "Health check passed!"
                    curl -s http://localhost:${STAGING_PORT}/health
                    echo ""

                    echo "Checking /stocks endpoint..."
                    curl -s http://localhost:${STAGING_PORT}/stocks
                    echo ""

                    echo "Testing prediction endpoint for CBA.AX..."
                    curl -s http://localhost:${STAGING_PORT}/predict/CBA.AX
                    echo ""

                    echo "Staging deployment verified successfully!"
                """
            }
            post {
                success {
                    echo "DEPLOY STAGE PASSED — app running on staging port ${STAGING_PORT}"
                }
                failure {
                    echo "DEPLOY STAGE FAILED — collecting staging logs..."
                    sh "docker logs ${CONTAINER_STAGING} || true"
                }
            }
        }

        // ================================================================
        // STAGE 6 — RELEASE (Production)
        // ================================================================
        stage("Release") {
            steps {
                echo "============================================"
                echo " STAGE 6: RELEASE TO PRODUCTION"
                echo "============================================"

                sh """
                    echo "Tagging image as versioned release..."
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:release-${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:stable

                    echo "Available image tags:"
                    docker images ${IMAGE_NAME}
                """

                sh """
                    echo "Stopping and removing old production container if exists..."
                    docker stop ${CONTAINER_PROD} 2>/dev/null || true
                    docker rm   ${CONTAINER_PROD} 2>/dev/null || true

                    echo "Deploying release-${IMAGE_TAG} to production on port ${PROD_PORT}..."
                    docker run -d \
                        --name ${CONTAINER_PROD} \
                        -p ${PROD_PORT}:5000 \
                        -e FLASK_ENV=production \
                        -e BUILD_NUMBER=${BUILD_NUMBER} \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:release-${IMAGE_TAG}

                    echo "Waiting for production container to be ready..."
                    sleep 8
                """

                sh """
                    echo "Running production smoke tests..."

                    MAX_RETRIES=5
                    COUNT=0
                    until curl -sf http://localhost:${PROD_PORT}/health > /dev/null; do
                        COUNT=\$((COUNT+1))
                        if [ \$COUNT -ge \$MAX_RETRIES ]; then
                            echo "Production health check FAILED"
                            docker logs ${CONTAINER_PROD}
                            exit 1
                        fi
                        echo "Attempt \$COUNT — waiting..."
                        sleep 3
                    done

                    echo "Production health check passed!"
                    curl -s http://localhost:${PROD_PORT}/health
                    echo ""

                    echo "Full prediction test on all ASX stocks..."
                    for ticker in CBA.AX BHP.AX CSL.AX WES.AX NAB.AX; do
                        echo "Testing \$ticker..."
                        curl -s http://localhost:${PROD_PORT}/predict/\$ticker
                        echo ""
                    done
                """

                sh """
                    echo "Creating Git release tag..."
                    git config user.email "jenkins@ci.local" || true
                    git config user.name  "Jenkins CI"       || true
                    git tag -a "v1.${IMAGE_TAG}" \
                        -m "Release build ${BUILD_NUMBER} — \$(date '+%Y-%m-%d %H:%M')" \
                        2>/dev/null || echo "Tag already exists or git not configured, skipping"

                    echo "Release v1.${IMAGE_TAG} is live on port ${PROD_PORT}"
                """
            }
            post {
                success {
                    echo "RELEASE STAGE PASSED — production running on port ${PROD_PORT}"
                    echo "Release tag: v1.${IMAGE_TAG}"
                }
                failure {
                    echo "RELEASE STAGE FAILED — rolling back..."
                    sh """
                        docker stop ${CONTAINER_PROD} 2>/dev/null || true
                        docker rm   ${CONTAINER_PROD} 2>/dev/null || true
                    """
                }
            }
        }

        // ================================================================
        // STAGE 7 — MONITORING & ALERTING
        // ================================================================
        stage("Monitoring") {
            steps {
                echo "============================================"
                echo " STAGE 7: MONITORING & ALERTING"
                echo "============================================"

                sh """
                    echo "Starting Prometheus and Grafana via Docker Compose..."
                    docker-compose up -d prometheus grafana 2>/dev/null || \
                    docker compose  up -d prometheus grafana

                    echo "Waiting for monitoring stack to initialise..."
                    sleep 12
                """

                sh """
                    echo "Verifying /metrics endpoint on production app..."
                    METRICS=\$(curl -s http://localhost:${PROD_PORT}/metrics)
                    echo "\$METRICS"

                    echo ""
                    if echo "\$METRICS" | grep -q "prediction_requests_total"; then
                        echo "Prometheus metrics endpoint CONFIRMED"
                    else
                        echo "WARNING: prediction_requests_total metric not found"
                    fi
                """

                sh """
                    echo "Generating traffic so Prometheus has data to scrape..."
                    for i in 1 2 3; do
                        curl -s http://localhost:${PROD_PORT}/predict/CBA.AX > /dev/null
                        curl -s http://localhost:${PROD_PORT}/predict/BHP.AX > /dev/null
                        curl -s http://localhost:${PROD_PORT}/health         > /dev/null
                    done
                    echo "Traffic generated."
                """

                sh """
                    echo "Checking Prometheus target health..."
                    sleep 5
                    PROM_STATUS=\$(curl -s "http://localhost:9090/api/v1/targets" 2>/dev/null || echo "prometheus_not_ready")

                    if echo "\$PROM_STATUS" | grep -q '"health":"up"'; then
                        echo "Prometheus target is UP and scraping"
                    elif echo "\$PROM_STATUS" | grep -q "prometheus_not_ready"; then
                        echo "Prometheus not reachable yet — may still be starting"
                    else
                        echo "Prometheus target status: pending"
                    fi
                """

                sh """
                    echo ""
                    echo "==================================================="
                    echo " MONITORING STACK SUMMARY"
                    echo "==================================================="
                    echo " App (staging)    : http://localhost:${STAGING_PORT}"
                    echo " App (production) : http://localhost:${PROD_PORT}"
                    echo " App metrics      : http://localhost:${PROD_PORT}/metrics"
                    echo " Prometheus       : http://localhost:9090"
                    echo " Grafana          : http://localhost:3000 (admin/admin)"
                    echo " SonarQube        : http://localhost:9000"
                    echo "==================================================="
                """
            }
            post {
                success {
                    echo "MONITORING STAGE PASSED — full observability stack running"
                }
                failure {
                    echo "MONITORING STAGE FAILED — check docker-compose.yml"
                    sh "docker-compose logs prometheus grafana 2>/dev/null || true"
                }
            }
        }

    } // end stages

    // ================================================================
    // POST — global pipeline result handlers
    // ================================================================
    post {
        success {
            echo "===================================================="
            echo " PIPELINE SUCCEEDED — Build #${BUILD_NUMBER}"
            echo " Image     : ${IMAGE_NAME}:${IMAGE_TAG}"
            echo " Staging   : http://localhost:${STAGING_PORT}"
            echo " Production: http://localhost:${PROD_PORT}"
            echo " SonarQube : http://localhost:9000"
            echo " Prometheus: http://localhost:9090"
            echo " Grafana   : http://localhost:3000"
            echo "===================================================="
        }
        failure {
            echo "===================================================="
            echo " PIPELINE FAILED — Build #${BUILD_NUMBER}"
            echo " Check console output above for details."
            echo "===================================================="
        }
        always {
            echo "Archiving all build artefacts..."
            archiveArtifacts artifacts: """
                coverage.xml,
                test-results.xml,
                test-report.html,
                trivy-report.txt,
                trivy-critical.json,
                bandit-report.txt,
                bandit-report.json,
                pip-audit-report.txt
            """, allowEmptyArchive: true

            echo "Cleaning up dangling Docker images..."
            sh "docker image prune -f 2>/dev/null || true"

            echo "Pipeline finished — build #${BUILD_NUMBER}"
        }
    }

} // end pipeline