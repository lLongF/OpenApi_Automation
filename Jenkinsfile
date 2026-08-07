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
        stage('拉取代码') {
            steps {
                git url: '你的仓库地址', branch: 'main'
            }
        }

        stage('推送代码到远端测试服务器') {
            steps {
                // 把整个项目代码推送到远端服务器 /opt/api_test 目录
                sshPublisher(publishers: [
                    sshPublisherDesc(
                        configName: "api‑test‑server", // Publish Over SSH配置里的服务器名字
                        transfers: [
                            sshTransfer(
                                sourceFiles: "**",
                                removePrefix: "",
                                remoteDirectory: "/opt/api_test",
                                cleanRemote: false // 不要轻易开true，会清空服务器目录
                            )
                        ]
                    )
                ])
            }
        }

        stage('远程调用服务器执行 run_test.sh') {
            steps {
                withCredentials([
                    string(credentialsId: 'test-user-id', variable: 'SHANHAI_USER_ID'),
                    string(credentialsId: 'test-admin-token', variable: 'SHANHAI_ADMIN_TOKEN')
                ]) {
                    script {
                        def scope = params.TEST_SCOPE
                        def syncFlag = params.SYNC_OPENAPI.toString()

                        // ssh远程执行脚本，把参数和密钥环境变量传给远端shell
                        sshCommand remote: 'api‑test‑server', command: """
cd /opt/api_test && \
export SHANHAI_USER_ID='${SHANHAI_USER_ID}' && \
export SHANHAI_ADMIN_TOKEN='${SHANHAI_ADMIN_TOKEN}' && \
chmod +x run_test.sh && \
./run_test.sh ${scope} ${syncFlag}
"""
                    }
                }
            }
        }

        stage('拉回测试报告到Jenkins归档') {
            steps {
                sshPublisher(publishers: [
                    sshPublisherDesc(
                        configName: "api‑test‑server",
                        transfers: [
                            sshTransfer(
                                sourceFiles: "/opt/api_test/reports/**",
                                remoteDirectory: "",
                                localDirectory: "./reports"
                            )
                        ]
                    )
                ])
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