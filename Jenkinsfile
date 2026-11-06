
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
    }

    environment {
        IMAGE = "attendance-system"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code from GitHub...'
                checkout scm
            }
        }

        stage('Install') {
            steps {
                bat 'python --version'
                bat 'python -m venv venv'
                bat 'venv\\Scripts\\python.exe -m pip install --upgrade pip'
                bat 'venv\\Scripts\\python.exe -m pip install -r requirements.txt flake8 pytest'
            }
        }

        stage('Lint') {
            steps {
                bat 'venv\\Scripts\\python.exe -m flake8 app.py'
            }
        }

        stage('Unit Tests') {
            steps {
                bat 'venv\\Scripts\\python.exe -m pytest -v'
            }
        }

        stage('Docker Build') {
            steps {
                bat 'docker build -t %IMAGE%:%BUILD_NUMBER% -t %IMAGE%:latest .'
            }
        }

        stage('Deploy') {
            steps {
                bat 'docker rm -f attendance 2>NUL || ver >NUL'
                bat 'docker run -d --name attendance -p 5000:5000 %IMAGE%:latest'
                bat 'timeout /t 5 /nobreak >NUL'
            }
        }

        stage('Selenium Tests') {
            steps {
                bat 'set "BASE_URL=http://localhost:5000" && venv\\Scripts\\python.exe -m pytest selenium_tests -v'
            }
        }
    }

    post {
        success {
            echo 'Attendance System CI/CD pipeline completed successfully!'
        }

        failure {
            echo 'Pipeline failed. Checking Docker logs...'
            bat 'docker logs attendance 2>NUL || ver >NUL'
        }
    }
}
