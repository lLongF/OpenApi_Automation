pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '15'))
  }

  parameters {
    choice(name: 'TEST_SCOPE', choices: ['smoke', 'all'], description: 'smoke：核心用例；all：全部测试用例')
    booleanParam(name: 'SYNC_OPENAPI', defaultValue: false, description: '执行前同步 Apifox/OpenAPI 并生成用例模板')
  }

  stages {
    stage('检查运行环境') {
      steps {
        sh 'python3 --version'
        sh 'git --version'
        // 直接从容器内jenkins_home目录复制素材到工作区
        sh '''
        rm -rf data/mock_files
        cp -r /var/jenkins_home/mock_media_fixtures data/mock_files
        '''
      }
    }

    stage('创建虚拟环境并安装依赖') {
      steps {
        sh '''
        rm -rf .venv
        python3 -m venv .venv
        .venv/bin/python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
        .venv/bin/python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        '''
      }
    }

    stage('执行测试环境接口测试') {
      steps {
        withCredentials([
          string(credentialsId: 'test-user-id', variable: 'SHANHAI_USER_ID'),
          string(credentialsId: 'test-admin-token', variable: 'SHANHAI_ADMIN_TOKEN')
        ]) {
          script {
            def marker = params.TEST_SCOPE == 'smoke' ? '-m smoke' : ''
            def syncOption = params.SYNC_OPENAPI ? '' : '--no-openapi-case-sync'

            sh """
            export TEST_ENV=test
            export SHANHAI_USER_ID='${SHANHAI_USER_ID}'
            export SHANHAI_ADMIN_TOKEN='${SHANHAI_ADMIN_TOKEN}'
            mkdir -p reports
            .venv/bin/python -m pytest tests --live --env test ${marker} ${syncOption} --clean-alluredir --alluredir=reports/allure-results --junitxml=reports/junit.xml
            """
          }
        }
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: 'reports/junit.xml'
      archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
    }
  }
}