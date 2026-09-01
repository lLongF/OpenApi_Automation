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
        unstable {
            sendWecomNotice()
        }
        failure {
            sendWecomNotice()
        }
    }
}

def sendWecomNotice() {
    withCredentials([
        string(credentialsId: 'wecom-webhook', variable: 'WECOM_WEBHOOK')
    ]) {
        sh '''
python3 - <<'PY' > reports/wecom-failure.json
import json
import os
import textwrap
from pathlib import Path

results_dir = Path("reports/allure-results")
build = "#" + os.getenv("BUILD_NUMBER", "unknown")
title = "OpenAPI 自动化测试报告"
failures = []

def read_attachment(source):
    if not source:
        return ""
    path = results_dir / source
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()

for result_path in sorted(results_dir.glob("*-result.json")):
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    if result.get("status") not in {"failed", "broken"}:
        continue
    case_name = result.get("name") or result.get("fullName") or "未命名用例"
    interface = ""
    for parameter in result.get("parameters", []):
        if parameter.get("name") == "Full interface URL":
            interface = str(parameter.get("value", "")).strip("'")
            break
    error_log = (result.get("statusDetails") or {}).get("message", "")
    for attachment in result.get("attachments", []):
        attachment_name = attachment.get("name")
        content = read_attachment(attachment.get("source"))
        if attachment_name == "Full interface URL" and content:
            interface = content
        elif attachment_name == "Failure reason" and content:
            error_log = content
    failures.append({
        "case_name": case_name,
        "interface": interface or "未从 Allure 报告中提取到接口",
        "error_log": error_log or "未从 Allure 报告中提取到失败详情",
    })

if not failures:
    failures.append({
        "case_name": "未找到失败用例",
        "interface": "未从 Allure 报告中提取到接口",
        "error_log": "请确认 reports/allure-results 已生成并被保留。",
    })

items = []
for index, item in enumerate(failures[:5], start=1):
    error_log = textwrap.shorten(
        " ".join(item["error_log"].split()),
        width=1200,
        placeholder=" ...（响应已截断）",
    )
    part1 = "### 失败用例 " + str(index) + "：" + item['case_name'] + "\\n"
    part2 = "> 接口：`" + item['interface'] + "`\\n"
    part3 = "> 结果：<font color=\\"warning\\">失败</font>\\n\\n"
    part4 = "**接口响应信息：**\\n```text\\n" + response_info + "\\n```"
    items.append(part1 + part2 + part3 + part4)

remaining = len(failures) - 5
extra = ""
if remaining > 0:
    extra = "\\n\\n另有 " + str(remaining) + " 条失败用例未展示。"

content = "## " + title + "\\n"
content += "> 构建：" + build + "\\n"
content += "> 报告：OpenAPI 接口自动化测试\\n"
content += "> 描述：执行接口自动化回归测试\\n"
content += "> 结果：<font color=\\"warning\\">失败（共 " + str(len(failures)) + " 条）</font>\\n\\n"
content += "\\n\\n".join(items)
content += extra

payload = {
    "msgtype": "markdown",
    "markdown": {
        "content": content
    }
}
print(json.dumps(payload, ensure_ascii=False))
PY

curl --fail --silent --show-error \
    --request POST "$WECOM_WEBHOOK" \
    --header 'Content-Type: application/json' \
    --data-binary @reports/wecom-failure.json
'''
    }
}
