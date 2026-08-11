pipeline {
  agent any
  options { timestamps() }
  parameters {
    choice(name: 'TEST_SCOPE', choices: ['smoke', 'all'], description: '测试范围')
    booleanParam(name: 'SYNC_OPENAPI', defaultValue: false, description: '是否同步openapi用例')
  }
  stages {
    stage('Git LFS SSH模式拉取素材') {
      steps {
        sh '''
        # CI环境不要执行 git lfs install，会操作hooks报错
        git config lfs.sshcommand ssh || true
        git config lfs.transfer.ssh true || true
        # --skip-repo 跳过安装hooks，仅执行下载
        git lfs pull --skip-repo || true
        echo "====校验媒体文件是否为真实二进制===="
        ls -lh test_assets/*.wav test_assets/*.mp3 test_assets/*.mp4 2>/dev/null || true
        echo "====查看第一个文件头部判断是否LFS指针===="
        head -c 200 test_assets/valid_audio.wav 2>/dev/null || echo "文件不存在"
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