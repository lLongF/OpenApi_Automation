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
                        def marker = '-m "not openapi"'
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
        failure {
            sendWecomAlert()
        }
        unstable {
            sendWecomAlert()
        }
    }
}

def sendWecomAlert(){
    withCredentials([
        string(credentialsId: 'wecom-webhook', variable: 'WECOM_WEBHOOK')
    ]) {
        sh '''
          python3 - <<'PY' > reports/wecom-failure.json
import json
import os
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

report_path = Path("reports/junit.xml")
title = "OpenAPI 自动化测试报告"
build = f"#{os.getenv('BUILD_NUMBER', 'unknown')}"
interface = "未从报告中提取到接口"
error_log = "未找到失败详情"

if report_path.exists():
    root = ET.parse(report_path).getroot()
    for case in root.iter("testcase"):
        failure = case.find("failure") or case.find("error")
        if failure is None:
            continue
        interface = case.get("name", interface)
        error_log = failure.get("message") or (failure.text or error_log)
        break

error_log = textwrap.shorten(
    " ".join(error_log.split()),
    width=1500,
    placeholder=" ...（日志已截断）",
)

content = (
    f"## {title}\\n"
    f"> 构建：{build}\\n"
    f"> 报告：{title}\\n"
    f"> 接口：`{interface}`\\n"
    f"> 结果：<font color=\\"warning\\">失败</font>\\n\\n"
    f"**错误日志：**\\n```text\\n{error_log}\\n```"
)

print(json.dumps(
    {"msgtype": "markdown", "markdown": {"content": content}},
    ensure_ascii=False,
))
PY
          curl --fail --silent --show-error \
            --request POST "$WECOM_WEBHOOK" \
            --header 'Content-Type: application/json' \
            --data-binary @reports/wecom-failure.json
        '''
    }
}
