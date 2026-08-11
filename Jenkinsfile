pipeline {
  agent any
  options { timestamps() }
  parameters {
    choice(name: 'TEST_SCOPE', choices: ['smoke', 'all'], description: '测试范围')
    booleanParam(name: 'SYNC_OPENAPI', defaultValue: false, description: '是否同步openapi用例')
  }
  stages {
    stage('拉取代码 & Git LFS 修复(SSH模式)') {
      steps {
        // SCM已经自动checkout完毕，直接配置lfs使用ssh
        sh '''
        git lfs install
        # 开启LFS使用SSH协议传输，绕过https访问失败问题
        git config lfs.sshcommand ssh
        git config lfs.transfer.ssh true
        git lfs pull || true
        echo "====校验媒体文件是否为真实二进制，不是指针===="
        ls -lh test_assets/*.wav test_assets/*.mp3 test_assets/*.mp4 2>/dev/null || true
        '''
      }
    }
    stage('检查环境') {
      steps {
        script {
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
            def marker = params.TEST_SCOPE == 'smoke' ? '-m smoke' : ''
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