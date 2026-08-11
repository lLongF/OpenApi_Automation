pipeline {
  agent any
  options { timestamps() }
  parameters {
    choice(name: 'TEST_SCOPE', choices: ['smoke', 'all'], description: '测试范围')
    booleanParam(name: 'SYNC_OPENAPI', defaultValue: false, description: '是否同步openapi用例')
  }
  stages {
    stage('检查环境') {
      steps {
        script {
          def allureHome = tool('allure')
          env.ALLURE_BIN = "${allureHome}/bin/allure"
          sh 'python3 --version'
          sh "${env.ALLURE_BIN} --version"
        }
        // 【关键！恢复旧版成功逻辑，拷贝jenkins全局预置媒体fixture】
        sh '''
        rm -rf data/mock_files
        cp -r /var/jenkins_home/mock_media_fixtures data/mock_files
        '''
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
    stage('执行冒烟测试') {
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
            def marker = ''
            def syncOpt = params.SYNC_OPENAPI ? '' : '--no-openapi-case-sync'
            sh returnStatus: true, script: '''
              export TEST_ENV=test
              mkdir -p reports
              .venv/bin/python -m pytest tests --live --env test '''+marker+''' '''+syncOpt+''' --clean-alluredir --alluredir=reports/allure-results --junitxml=reports/junit.xml
            '''
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
        reportDir: 'reports', reportFiles: 'report.html', reportName: 'Pytest HTML Report'
      ])
      publishHTML(target: [
        allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true,
        reportDir: 'reports/allure-report', reportFiles: 'index.html', reportName: 'Allure Report'
      ])
    }
  }
}
