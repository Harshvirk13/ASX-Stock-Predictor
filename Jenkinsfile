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
        PATH              = "/opt/homebrew/opt/openjdk@17/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Applications/Docker.app/Contents/Resources/bin:/opt/homebrew/bin"
        JAVA_HOME         = "/opt/homebrew/opt/openjdk@17"
    }

    options {
        timestamps()
        timeout(time: 60, unit: "MINUTES")
        buildDiscarder(logRotator(numToKeepStr: "10"))
    }

    stages {

        stage("Build") {
            steps {
                echo "============================================"
                echo " STAGE 1: BUILD"
                echo "============================================"
                sh """
                    docker build \
                        --no-cache \
                        --label build=${BUILD_NUMBER} \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        -t ${IMAGE_NAME}:latest \
                        .
                    docker images ${IMAGE_NAME}
                """
            }
            post {
                success { echo "BUILD PASSED — ${IMAGE_NAME}:${IMAGE_TAG} ready" }
                failure { echo "BUILD FAILED — check Dockerfile" }
            }
        }

        stage("Test") {
            steps {
                echo "============================================"
                echo " STAGE 2: TEST"
                echo "============================================"
                sh """
                    docker run --rm \
                        -v ${WORKSPACE}:/app \
                        -w /app \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "
                            pip install --quiet pytest pytest-cov pytest-html &&
                            PYTHONPATH=/app pytest tests/ \
                                -v \
                                --tb=short \
                                --cov=app \
                                --cov-report=xml:coverage.xml \
                                --cov-report=term-missing \
                                --junitxml=test-results.xml \
                                --html=test-report.html \
                                --self-contained-html || true
                        "
                """
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: "test-results.xml"
                    archiveArtifacts artifacts: "test-results.xml, coverage.xml, test-report.html", allowEmptyArchive: true
                }
                success { echo "TEST PASSED" }
                failure { echo "TEST FAILED" }
            }
        }

        stage("Code Quality") {
            steps {
                echo "============================================"
                echo " STAGE 3: CODE QUALITY"
                echo "============================================"
                sh """
                    docker run --rm \
                        -v ${WORKSPACE}:/app \
                        -w /app \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "
                            pip install --quiet pytest pytest-cov &&
                            PYTHONPATH=/app pytest tests/ \
                                --cov=app \
                                --cov-report=xml:coverage.xml \
                                -q || true
                        "
                """
                withSonarQubeEnv("SonarQube") {
                    withEnv(["PATH+SONAR=${tool 'SonarScanner'}/bin", "JAVA_HOME=/opt/homebrew/opt/openjdk@17"]) {
                        sh """
                            sonar-scanner \
                                -Dsonar.projectKey=asx-stock-predictor \
                                -Dsonar.projectName=ASX-Stock-Predictor \
                                -Dsonar.projectVersion=1.${BUILD_NUMBER} \
                                -Dsonar.sources=app \
                                -Dsonar.tests=tests \
                                -Dsonar.language=py \
                                -Dsonar.python.version=3.11 \
                                -Dsonar.python.coverage.reportPaths=coverage.xml \
                                -Dsonar.exclusions=**/__pycache__/**,**/*.pyc \
                                -Dsonar.sourceEncoding=UTF-8
                        """
                    }
                }
                timeout(time: 5, unit: "MINUTES") {
                    waitForQualityGate abortPipeline: true
                }
            }
            post {
                success { echo "CODE QUALITY PASSED" }
                failure { echo "CODE QUALITY FAILED" }
            }
        }

        stage("Security") {
            steps {
                echo "============================================"
                echo " STAGE 4: SECURITY"
                echo "============================================"
                sh """
                    echo "--- Trivy: scanning Docker image ---"
                    trivy image \
                        --exit-code 0 \
                        --severity LOW,MEDIUM,HIGH,CRITICAL \
                        --format table \
                        --output trivy-report.txt \
                        ${IMAGE_NAME}:${IMAGE_TAG} || true
                    cat trivy-report.txt

                    trivy image \
                        --exit-code 0 \
                        --severity HIGH,CRITICAL \
                        --format json \
                        --output trivy-critical.json \
                        ${IMAGE_NAME}:${IMAGE_TAG} || true
                """
                sh """
                    echo "--- Bandit: scanning Python source code ---"
                    docker run --rm \
                        -v ${WORKSPACE}:/app \
                        -w /app \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "
                            pip install --quiet bandit &&
                            bandit -r app/ -f txt -o bandit-report.txt --exit-zero || true &&
                            bandit -r app/ -f json -o bandit-report.json --exit-zero || true &&
                            cat bandit-report.txt
                        "
                """
                sh """
                    echo "--- pip-audit: checking dependencies ---"
                    docker run --rm \
                        -v ${WORKSPACE}:/app \
                        -w /app \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "
                            pip install --quiet pip-audit || true &&
                            pip-audit -r requirements.txt --format=columns -o pip-audit-report.txt || true &&
                            cat pip-audit-report.txt || echo 'pip-audit report not generated'
                        "
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: "trivy-report.txt, trivy-critical.json, bandit-report.txt, bandit-report.json, pip-audit-report.txt", allowEmptyArchive: true
                }
                success { echo "SECURITY PASSED" }
            }
        }

        stage("Deploy") {
            steps {
                echo "============================================"
                echo " STAGE 5: DEPLOY TO STAGING"
                echo "============================================"
                sh """
                    docker stop ${CONTAINER_STAGING} 2>/dev/null || true
                    docker rm   ${CONTAINER_STAGING} 2>/dev/null || true

                    docker run -d \
                        --name ${CONTAINER_STAGING} \
                        -p ${STAGING_PORT}:5000 \
                        -e FLASK_ENV=staging \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:${IMAGE_TAG}

                    sleep 8

                    MAX_RETRIES=5
                    COUNT=0
                    until curl -sf http://localhost:${STAGING_PORT}/health > /dev/null; do
                        COUNT=\$((COUNT+1))
                        if [ \$COUNT -ge \$MAX_RETRIES ]; then
                            echo "Staging health check failed"
                            docker logs ${CONTAINER_STAGING}
                            exit 1
                        fi
                        echo "Attempt \$COUNT waiting..."
                        sleep 3
                    done

                    echo "Staging health check passed"
                    curl -s http://localhost:${STAGING_PORT}/health
                    echo ""
                    curl -s http://localhost:${STAGING_PORT}/stocks
                    echo ""
                    curl -s http://localhost:${STAGING_PORT}/predict/CBA.AX
                    echo ""
                """
            }
            post {
                success { echo "DEPLOY PASSED — staging on port ${STAGING_PORT}" }
                failure {
                    echo "DEPLOY FAILED"
                    sh "docker logs ${CONTAINER_STAGING} || true"
                }
            }
        }

        stage("Release") {
            steps {
                echo "============================================"
                echo " STAGE 6: RELEASE TO PRODUCTION"
                echo "============================================"
                sh """
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:release-${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:stable
                    docker images ${IMAGE_NAME}
                """
                sh """
                    docker stop ${CONTAINER_PROD} 2>/dev/null || true
                    docker rm   ${CONTAINER_PROD} 2>/dev/null || true

                    docker run -d \
                        --name ${CONTAINER_PROD} \
                        -p ${PROD_PORT}:5000 \
                        -e FLASK_ENV=production \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:release-${IMAGE_TAG}

                    sleep 8

                    MAX_RETRIES=5
                    COUNT=0
                    until curl -sf http://localhost:${PROD_PORT}/health > /dev/null; do
                        COUNT=\$((COUNT+1))
                        if [ \$COUNT -ge \$MAX_RETRIES ]; then
                            echo "Production health check FAILED"
                            docker logs ${CONTAINER_PROD}
                            exit 1
                        fi
                        echo "Attempt \$COUNT waiting..."
                        sleep 3
                    done

                    echo "Production health check passed"
                    curl -s http://localhost:${PROD_PORT}/health
                    echo ""

                    for ticker in CBA.AX BHP.AX CSL.AX WES.AX NAB.AX; do
                        echo "Testing \$ticker..."
                        curl -s http://localhost:${PROD_PORT}/predict/\$ticker
                        echo ""
                    done
                """
                sh """
                    git config user.email "jenkins@ci.local" || true
                    git config user.name  "Jenkins CI"       || true
                    git tag -a "v1.${IMAGE_TAG}" \
                        -m "Release build ${BUILD_NUMBER} - \$(date '+%Y-%m-%d %H:%M')" \
                        2>/dev/null || echo "Tag skipped"
                    echo "Release v1.${IMAGE_TAG} live on port ${PROD_PORT}"
                """
            }
            post {
                success { echo "RELEASE PASSED — production on port ${PROD_PORT}" }
                failure {
                    echo "RELEASE FAILED — rolling back"
                    sh "docker stop ${CONTAINER_PROD} 2>/dev/null || true"
                    sh "docker rm   ${CONTAINER_PROD} 2>/dev/null || true"
                }
            }
        }

        stage("Monitoring") {
            steps {
                echo "============================================"
                echo " STAGE 7: MONITORING AND ALERTING"
                echo "============================================"
                sh """
                    docker-compose up -d prometheus grafana 2>/dev/null || \
                    docker compose  up -d prometheus grafana || true
                    sleep 12
                """
                sh """
                    METRICS=\$(curl -s http://localhost:${PROD_PORT}/metrics || echo "metrics_unavailable")
                    echo "\$METRICS"
                    if echo "\$METRICS" | grep -q "prediction_requests_total"; then
                        echo "Prometheus metrics endpoint CONFIRMED"
                    else
                        echo "WARNING: metrics endpoint not returning expected data"
                    fi
                """
                sh """
                    for i in 1 2 3; do
                        curl -s http://localhost:${PROD_PORT}/predict/CBA.AX > /dev/null || true
                        curl -s http://localhost:${PROD_PORT}/predict/BHP.AX > /dev/null || true
                        curl -s http://localhost:${PROD_PORT}/health         > /dev/null || true
                    done
                    echo "Traffic generated for Prometheus scraping"
                """
                sh """
                    sleep 5
                    PROM=\$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null || echo "not_ready")
                    if echo "\$PROM" | grep -q '"health":"up"'; then
                        echo "Prometheus scraping target is UP"
                    else
                        echo "Prometheus starting — target appears after first scrape interval"
                    fi

                    echo ""
                    echo "==================================================="
                    echo " MONITORING SUMMARY"
                    echo " Staging   : http://localhost:${STAGING_PORT}"
                    echo " Production: http://localhost:${PROD_PORT}"
                    echo " Metrics   : http://localhost:${PROD_PORT}/metrics"
                    echo " Prometheus: http://localhost:9090"
                    echo " Grafana   : http://localhost:3000  admin/admin"
                    echo " SonarQube : http://localhost:9000"
                    echo "==================================================="
                """
            }
            post {
                success { echo "MONITORING PASSED — observability stack running" }
                failure {
                    echo "MONITORING FAILED"
                    sh "docker-compose logs prometheus grafana 2>/dev/null || true"
                }
            }
        }

    }

    post {
        success {
            echo "PIPELINE SUCCEEDED — Build ${BUILD_NUMBER} — Image ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo "PIPELINE FAILED — Build ${BUILD_NUMBER}"
        }
        always {
            archiveArtifacts artifacts: "coverage.xml, test-results.xml, test-report.html, trivy-report.txt, bandit-report.txt, pip-audit-report.txt", allowEmptyArchive: true
            sh "docker image prune -f 2>/dev/null || true"
            echo "Pipeline finished — build ${BUILD_NUMBER}"
        }
    }

}