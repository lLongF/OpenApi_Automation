pipeline {
  agent any
  options { timestamps() }
  tools { allure 'allure' } // 对应全局工具别名
  parameters {
    choice(name: 'TEST_SCOPE', choices: ['smoke', 'all'])
    booleanParam(name: 'SYNC_OPENAPI', defaultValue: false)
  }
  stages {
    stage('检查环境') {
      steps {
        sh 'python3 --version'
        sh 'allure --version'
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
            sh 'allure generate reports/allure-results -o reports/allure-report --clean'
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