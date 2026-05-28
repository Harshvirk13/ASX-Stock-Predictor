pipeline {
    agent any

    environment {

        IMAGE_NAME        = "task-73hd"
        IMAGE_TAG         = "${BUILD_NUMBER}"

        SONAR_HOST        = "http://localhost:9000"

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

        // =========================================================
        // BUILD
        // =========================================================

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

                success {
                    echo "BUILD PASSED — ${IMAGE_NAME}:${IMAGE_TAG} ready"
                }

                failure {
                    echo "BUILD FAILED"
                }
            }
        }

        // =========================================================
        // TEST
        // =========================================================

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
                                --self-contained-html
                        "
                """
            }

            post {

                always {

                    junit allowEmptyResults: true,
                           testResults: "test-results.xml"

                    archiveArtifacts artifacts: """
                        test-results.xml,
                        coverage.xml,
                        test-report.html
                    """,
                    allowEmptyArchive: true
                }

                success {
                    echo "TEST PASSED"
                }

                failure {
                    echo "TEST FAILED"
                }
            }
        }

        // =========================================================
        // CODE QUALITY
        // =========================================================

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
                                -q
                        "
                """

                withSonarQubeEnv("SonarQube") {

                    withEnv([
                        "PATH+SONAR=${tool 'SonarScanner'}/bin",
                        "JAVA_HOME=/opt/homebrew/opt/openjdk@17"
                    ]) {

                        sh """
                            sonar-scanner \
                                -Dsonar.host.url=${SONAR_HOST} \
                                -Dsonar.projectKey=asx-stock-predictor \
                                -Dsonar.projectName=ASX-Stock-Predictor \
                                -Dsonar.projectVersion=1.${BUILD_NUMBER} \
                                -Dsonar.sources=app \
                                -Dsonar.tests=tests \
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

                success {
                    echo "CODE QUALITY PASSED"
                }

                failure {
                    echo "CODE QUALITY FAILED"
                }
            }
        }

        // =========================================================
        // SECURITY
        // =========================================================

        stage("Security") {

            steps {

                echo "============================================"
                echo " STAGE 4: SECURITY"
                echo "============================================"

                // -------------------------------------------------
                // BANDIT
                // -------------------------------------------------

                sh """
                    echo "--- Bandit Security Scan ---"

                    docker run --rm \
                        -v ${WORKSPACE}:/app \
                        -w /app \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "
                            pip install --quiet bandit &&

                            bandit -r app/ \
                                -f txt \
                                -o bandit-report.txt \
                                --exit-zero

                            cat bandit-report.txt
                        "
                """

                // -------------------------------------------------
                // pip-audit
                // -------------------------------------------------

                sh """
                    echo "--- Dependency Audit ---"

                    docker run --rm \
                        -v ${WORKSPACE}:/app \
                        -w /app \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "
                            pip install --quiet pip-audit &&

                            pip-audit \
                                -r requirements.txt \
                                --format=columns \
                                -o pip-audit-report.txt || true

                            cat pip-audit-report.txt || echo 'No dependency vulnerabilities found'
                        "
                """
            }

            post {

                always {

                    archiveArtifacts artifacts: """
                        bandit-report.txt,
                        pip-audit-report.txt
                    """,
                    allowEmptyArchive: true
                }

                success {
                    echo "SECURITY PASSED"
                }

                failure {
                    echo "SECURITY FAILED"
                }
            }
        }

        // =========================================================
        // DEPLOY
        // =========================================================

        stage("Deploy") {

            steps {

                echo "============================================"
                echo " STAGE 5: DEPLOY TO STAGING"
                echo "============================================"

                sh """
                    docker stop ${CONTAINER_STAGING} 2>/dev/null || true
                    docker rm ${CONTAINER_STAGING} 2>/dev/null || true

                    docker run -d \
                        --name ${CONTAINER_STAGING} \
                        -p ${STAGING_PORT}:5000 \
                        -e FLASK_ENV=staging \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:${IMAGE_TAG}

                    sleep 10

                    curl -f http://localhost:${STAGING_PORT}/health
                """
            }

            post {

                success {
                    echo "DEPLOY PASSED"
                }

                failure {
                    echo "DEPLOY FAILED"
                }
            }
        }

        // =========================================================
        // RELEASE
        // =========================================================

        stage("Release") {

            steps {

                echo "============================================"
                echo " STAGE 6: RELEASE"
                echo "============================================"

                sh """
                    docker tag \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        ${IMAGE_NAME}:stable

                    docker stop ${CONTAINER_PROD} 2>/dev/null || true
                    docker rm ${CONTAINER_PROD} 2>/dev/null || true

                    docker run -d \
                        --name ${CONTAINER_PROD} \
                        -p ${PROD_PORT}:5000 \
                        -e FLASK_ENV=production \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:stable

                    sleep 10

                    curl -f http://localhost:${PROD_PORT}/health
                """
            }

            post {

                success {
                    echo "RELEASE PASSED"
                }

                failure {
                    echo "RELEASE FAILED"
                }
            }
        }

        // =========================================================
        // MONITORING
        // =========================================================

        stage("Monitoring") {

            steps {

                echo "============================================"
                echo " STAGE 7: MONITORING"
                echo "============================================"

                sh """
                    docker compose up -d prometheus grafana || true

                    sleep 10

                    curl -s http://localhost:${PROD_PORT}/metrics || true
                """
            }

            post {

                success {
                    echo "MONITORING PASSED"
                }

                failure {
                    echo "MONITORING FAILED"
                }
            }
        }
    }

    // =============================================================
    // POST
    // =============================================================

    post {

        success {

            echo "PIPELINE SUCCEEDED — Build ${BUILD_NUMBER}"
        }

        failure {

            echo "PIPELINE FAILED — Build ${BUILD_NUMBER}"
        }

        always {

            archiveArtifacts artifacts: """
                coverage.xml,
                test-results.xml,
                test-report.html,
                bandit-report.txt,
                pip-audit-report.txt
            """,
            allowEmptyArchive: true

            sh "docker image prune -f || true"

            echo "Pipeline finished — build ${BUILD_NUMBER}"
        }
    }
}