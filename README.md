# 山海智影 OpenAPI 接口自动化

基于 `pytest` 的 OpenAPI 接口自动化测试项目，覆盖语音克隆、语音合成、音色设计、字幕翻译、视频字幕/ASR、说话人分类、OpenAPI 契约检查等接口。

项目提供两种使用方式：

- Web 控制台：适合日常点选环境、模块并查看执行记录和 Allure 报告。
- 命令行：适合本地调试、CI 或精确运行某个测试文件/用例。

## 快速开始

```powershell
cd D:\Project\OpenApi_Automation
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts/install_allure.ps1
```

启动 Web 控制台：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_web.ps1 -Port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/
```

如果提示 `WinError 10048`，说明 `8000` 端口已经被占用。直接访问已有服务，或换端口启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_web.ps1 -Port 8001
```

## Web 控制台

Web 页面支持：

- 选择环境、模块、标记并启动测试。
- 查看运行日志和历史执行记录。
- 打开每次运行独立生成的 Allure 报告。
- 浏览和编辑 `data/test_data/*.yaml` 中的测试数据。

每次通过 Web 启动测试后，报告会生成在：

```text
reports/runs/<run_id>/allure-report/index.html
```

页面里的“报告”按钮会打开对应 run 的独立报告，避免多次运行互相覆盖导致 Allure 详情 404。

## 命令行运行

运行本地契约和非 live 用例：

```powershell
python -m pytest tests
```

运行真实接口用例：

```powershell
python -m pytest tests --live
```

只运行某个文件或用例：

```powershell
python -m pytest tests/test_voice.py --live
python -m pytest tests/test_videots.py::test_translate --live
```

按标记运行：

```powershell
python -m pytest tests -m smoke --live
python -m pytest tests -m negative --live
python -m pytest tests -m boundary --live
python -m pytest tests -m contract
python -m pytest tests -m openapi --live
```

Windows 一键脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Live
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Live -Marker "smoke"
```

## Allure 报告

pytest 结束后会自动生成 Allure HTML 报告。也可以手动重新生成：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate_allure_report.ps1
```

命令行默认报告位置：

```text
reports/allure-report/index.html
```

用静态服务查看：

```powershell
python -m http.server 8088 --directory reports
```

然后访问：

```text
http://127.0.0.1:8088/allure-report/index.html
```

不要直接双击 `index.html` 打开 Allure 报告，容易出现资源加载失败或 404。

## 目录说明

```text
config/
  env.yaml                    环境配置
  openapi_sources.yaml        Apifox / OpenAPI 同步配置

data/test_data/
  *.yaml                      按模块维护的测试数据
  files.yaml                  上传文件映射

data/mock_files/
  测试上传文件

src/openapi_automation/
  clients/                    API Client
  core/                       配置、HTTP、断言、文件加载
  contract/                   OpenAPI 同步和 diff

tests/
  test_*.py                   测试用例
  conftest.py                 pytest fixture 和 Allure 配置
  helpers.py                  通用断言、附件、日志辅助方法

scripts/
  start_web.ps1               启动 Web 控制台
  run_tests.ps1               Windows 一键运行测试
  install_allure.ps1          安装 Allure CLI
  generate_allure_report.ps1  生成 Allure 报告
  sync_openapi.py             同步 OpenAPI / Apifox
  validate_test_data.py       校验测试数据
```

## 测试数据

测试数据集中维护在：

```text
data/test_data/*.yaml
```

常见字段：

```yaml
id: 用例编号
title: 用例标题
category: positive / negative / boundary / exception
request: 请求数据
expected: 预期结果
http_status: 预期 HTTP 状态码
http_status_any: 允许多个 HTTP 状态码
code: 预期业务 code
code_any: 允许多个业务 code
message_contains: 响应信息需要包含的文本
message_contains_any: 命中任意一个文本即可
json_path_required: 指定 JSON 路径必须存在且非空
```

上传文件路径统一在 `data/test_data/files.yaml` 中维护。契约测试会检查这些文件是否真实存在于 `data/mock_files/`。

## OpenAPI / Apifox 契约检查

同步并生成 diff：

```powershell
python scripts/sync_openapi.py
```

接受新的基线：

```powershell
python scripts/sync_openapi.py --update-snapshot
```

通过 pytest 运行契约检查：

```powershell
python -m pytest tests/test_openapi_contract.py --live
```

常用输出：

```text
data/openapi/apifox_raw.json
data/openapi/apifox_latest.json
data/openapi/apifox_snapshot.json
reports/openapi/apifox_diff.json
reports/openapi/apifox_diff.md
```

## 常见问题

`WinError 10048`：端口已被占用。直接打开已有页面，或换端口启动。

Allure 详情页 404：通常是旧页面缓存或报告被新运行覆盖。关闭旧报告页，从 Web 控制台的对应执行记录重新点击“报告”。

live 用例被跳过：需要加 `--live`，并确认 `config/env.yaml` 或环境变量中配置了必要的 `user_id`、`api_key` 等信息。

OpenAPI document root must be an object：Apifox 地址返回的不是标准 OpenAPI JSON，可能是 HTML、错误信息、数组或空内容。
