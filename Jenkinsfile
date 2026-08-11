pipeline {
  agent any
  options { timestamps() }
  parameters {
    choice(name: 'TEST_SCOPE', choices: ['smoke', 'all'], description: '测试范围')
    booleanParam(name: 'SYNC_OPENAPI', defaultValue: false, description: '是否同步openapi用例')
  }
  stages {
    stage('下载测试媒体素材(绕过git‑lfs)') {
      steps {
        sh '''
        echo "清空原有assets媒体目录"
        rm -rf ./test_assets
        mkdir -p ./test_assets
        # ========== 这里替换成你内网可访问的素材压缩包地址 ==========
        wget -O test_assets.tar.gz http://内网静态地址/test_media_assets.tar.gz
        tar -zxvf test_assets.tar.gz -C ./test_assets
        rm -f test_assets.tar.gz
        echo "===== 校验解压后媒体文件大小 ====="
        find ./test_assets -name "*.wav" -o -name "*.mp3" -o -name "*.mp4" | xargs ls -lh
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
              # 告诉pytest素材读取目录，指向我们wget解压出来的目录，不再读取git lfs指针文件
              export TEST_ASSETS_ROOT="./test_assets"
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