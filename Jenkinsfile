pipeline {
  agent { label 'local-agent' }

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
      }
    }

    stage('创建虚拟环境并安装依赖') {
      steps {
        sh '''
python3 -m venv .venv
.venv/bin/python3 -m pip install --upgrade pip
.venv/bin/python3 -m pip install -r requirements.txt
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
.venv/bin/python3 -m pytest tests --live --env test ${marker} ${syncOption} --clean-alluredir --junitxml=reports/junit.xml
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
    failure {
      // 测试失败，流水线标记失败，上游发布流水线可以检测这个结果，阻断发布
      echo "❌接口自动化用例失败，阻断预发布流程"
    }
    success {
      echo "✅全部自动化用例执行通过，允许进入预发布流程"
    }
  }
}
