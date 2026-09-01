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
                        def marker = params.TEST_SCOPE == 'smoke' \
                            ? '-m "smoke and not openapi and not contract"' \
                            : '-m "not openapi and not contract"'
                        def syncOpt = params.SYNC_OPENAPI ? '' : '--no-openapi-case-sync'
                        sh returnStatus: true, script: '''
                          export TEST_ENV=test
                          mkdir -p reports
                          .venv/bin/python -m pytest tests --live --env test '''+marker+''' '''+syncOpt+''' --no-allure-report --clean-alluredir --alluredir=reports/allure-results --junitxml=reports/junit.xml
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
            sendWecomNotify()
        }
        unstable {
            sendWecomNotify()
        }
    }
}

def sendWecomNotify() {
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
build = os.getenv('BUILD_NUMBER', 'unknown')
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
    response_info = ""
    for parameter in result.get("parameters", []):
        if parameter.get("name") == "Full interface URL":
            interface = str(parameter.get("value", "")).strip("'")
            break
    for attachment in result.get("attachments", []):
        attachment_name = attachment.get("name")
        content = read_attachment(attachment.get("source"))
        if attachment_name == "Full interface URL" and content:
            interface = content
        elif attachment_name == "HTTP response" and content:
            response_info = content
       
    failures.append({
        "case_name": case_name,
        "interface": interface or "未从 Allure 报告中提取到接口",
        "response_info": response_info or "未从 Allure 报告中提取到接口响应信息",
    })

if not failures:
    failures.append({
        "case_name": "未找到失败用例",
        "interface": "未从 Allure 报告中提取到接口",
        "response_info": "请确认 reports/allure-results 已生成并被保留。",
    })
newline = chr(10)

items = []
for index, item in enumerate(failures[:5], start=1):
    response_info = textwrap.shorten(
        " ".join(item["response_info"].split()),
        width=1200,
        placeholder=" ...（响应已截断）",
    )
    
    items.append(newline.join([
        "### 失败用例 {}：{}".format(index, item["case_name"]),
        "> 接口：`{}`".format(item["interface"]),
        '> 结果：<font color="warning">失败</font>',
        "",
        "**接口响应信息：**",
        "```text",
        response_info,
        "```",
    ]))

remaining = len(failures) - 5
extra = (
    newline + newline + "另有 {} 条失败用例未展示。".format(remaining)
    if remaining > 0
    else ""
)

content = newline.join([
    "## {}".format(title),
    "> 构建：#{}".format(build),
    "> 报告：OpenAPI 接口自动化测试",
    "> 描述：执行接口自动化回归测试",
    '> 结果:<font color="warning">失败（共 {} 条）</font>'.format(len(failures)),
]) + newline + newline + (newline + newline).join(items) + extra

output = json.dumps(
    {"msgtype": "markdown", "markdown": {"content": content}},
    ensure_ascii=False,
)
print(output)
PY
curl --fail --silent --show-error \
    --request POST "$WECOM_WEBHOOK" \
    --header 'Content-Type: application/json' \
    --data-binary @reports/wecom-failure.json
        '''
    }
}
