pipeline {
  agent any
  options { timestamps() }
  parameters {
    choice(name: 'TEST_SCOPE', choices: ['smoke', 'all'])
    booleanParam(name: 'SYNC_OPENAPI', defaultValue: false)
  }
  stages {
    stage('检查环境') {
      steps {
        script {
          // 获取全局工具allure的根目录，显式拿到bin路径
          def allureHome = tool('allure')
          env.ALLURE_BIN = "${allureHome}/bin/allure"
          sh 'python3 --version'
          sh "${env.ALLURE_BIN} --version"
        }
      }
    }
    stage('安装依赖') {
      steps {
        sh '''
        rm -rf .venv
        python3 -m venv .venv
        .venv/bin/pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
        .venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        '''
      }
    }
    stage('执行测试') {
      steps {
        script {
          def allureHome = tool('allure')
          env.ALLURE_BIN = "${allureHome}/bin/allure"
        }
        withCredentials([
          string(credentialsId: 'test-user-id', variable: 'SHANHAI_USER_ID'),
          string(credentialsId: 'test-admin-token', variable: 'SHANHAI_ADMIN_TOKEN')
        ]) {
          script {
            def marker = params.TEST_SCOPE == 'smoke' ? '-m smoke' : ''
            def syncOpt = params.SYNC_OPENAPI ? '' : '--no-openapi-case-sync'
            sh returnStatus: true, script: '''
              export TEST_ENV=test
              mkdir -p reports
              .venv/bin/python -m pytest tests --live --env test '''+marker+''' '''+syncOpt+''' --clean-alluredir --alluredir=reports/allure-results --junitxml=reports/junit.xml
            '''
            // 不再直接写allure，使用环境变量完整二进制路径
            sh "${env.ALLURE_BIN} generate reports/allure-results -o reports/allure-report --clean"
          }
        }
      }
    }
  }
  post {
    always {
      junit allowEmptyResults: true, testResults: 'reports/junit.xml'
      archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
      publishHTML(target: [
        allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
        reportDir: 'reports', reportFiles: 'report.html', reportName: 'Pytest HTML'
      ])
      publishHTML(target: [
        allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
        reportDir: 'reports/allure-report', reportFiles: 'index.html', reportName: 'Allure Report'
      ])
    }
  }
}