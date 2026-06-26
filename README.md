# 山海智影 OpenAPI 接口自动化项目1111111

这是一个基于 `pytest` 的 OpenAPI 接口自动化测试项目，主要覆盖语音克隆、语音合成、音色设计、字幕翻译、视频字幕/ASR、说话人分类、OpenAPI 契约检查等接口。

项目已经接入 Allure 报告。报告中会展示用例标题、接口入参、接口出参、预期结果和失败原因。

## 项目结构

```text
config/
  env.yaml                    环境配置：base_url、user_id、admin_token、超时、重试等
  openapi_sources.yaml        Apifox / OpenAPI 契约同步配置

data/
  test_data/                  按接口拆分维护的测试数据 YAML
  test_data.yaml              测试数据入口说明，不再直接维护接口用例
  mock_files/                 文件上传类接口使用的测试文件
  openapi/                    OpenAPI 快照、最新同步文件、原始导出文件

src/openapi_automation/
  clients/                    API client 封装
  core/                       配置读取、HTTP 请求、断言、文件加载等基础能力
  contract/                   OpenAPI 契约同步、规范化、diff 对比

tests/
  conftest.py                 pytest fixture、Allure 套件名、运行参数
  helpers.py                  通用请求、断言、Allure 附件、接口关联辅助方法
  test_voice.py               语音克隆、语音合成
  test_timbre_design.py       音色设计
  test_videots.py             字幕翻译、回译、状态查询
  test_subtitle_asr_speaker.py 视频字幕擦除、ASR 相关接口
  test_speaker_classify.py    说话人分类提交、状态查询
  test_contract_data.py       测试数据契约检查
  test_openapi_contract.py    OpenAPI / Apifox 契约检查

scripts/
  validate_test_data.py       校验 test_data/*.yaml 格式和中文引号
  install_allure.ps1          Windows 安装 Allure CLI
  generate_allure_report.ps1  根据 allure-results 生成 allure-report
  run_tests.ps1               Windows 一键运行测试并生成 Allure 报告
  sync_openapi.py             同步 Apifox / OpenAPI 文档并生成 diff
```

## 安装依赖

先进入项目目录：

```powershell
cd D:\Project\OpenApi_Automation
```

安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
# 如果当前环境使用 Python 3 命令：
python3 -m pip install -r requirements.txt
```

安装 Allure CLI：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_allure.ps1
```

如果当前环境将 Python 3 命令配置为 `python3`，请使用下面每组命令中的 `python3` 版本；同一组中的两条命令等价，只需执行其中一条。



## 常用运行命令

运行所有非 live 用例：

```powershell
python -m pytest tests
python3 -m pytest tests
```

运行所有 live 用例，也就是会请求真实接口的用例：

```powershell
python -m pytest tests -m live --live
python3 -m pytest tests -m live --live
```

只运行某一个文件：

```powershell
python -m pytest tests/test_voice.py --live
python3 -m pytest tests/test_voice.py --live
```

只运行某一个用例：

```powershell
python -m pytest tests/test_videots.py::test_translate --live
python3 -m pytest tests/test_videots.py::test_translate --live
```

按标记运行：

```powershell
python -m pytest tests -m smoke --live
python3 -m pytest tests -m smoke --live
python -m pytest tests -m negative --live
python3 -m pytest tests -m negative --live
python -m pytest tests -m boundary --live
python3 -m pytest tests -m boundary --live
python -m pytest tests -m contract
python3 -m pytest tests -m contract
python -m pytest tests -m openapi --live
python3 -m pytest tests -m openapi --live
```

说明：

- `-m live`：只筛选带 `@pytest.mark.live` 的用例。
- `--live`：允许真实接口测试执行；不加时 live 用例会跳过。
- `-m contract`：运行本地契约检查，通常不请求业务接口。
- `-m openapi --live`：运行 OpenAPI / Apifox 契约同步检查。

## 运行并生成 Allure 报告

方式一：直接运行 pytest。pytest 结束后会自动生成 Allure HTML 报告。

运行用例并生成最新报告：

```powershell
python -m pytest tests --live --alluredir=reports/allure-results --clean-alluredir
python3 -m pytest tests --live --alluredir=reports/allure-results --clean-alluredir
```

如果只想手动重新生成 Allure HTML 报告，也可以单独执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate_allure_report.ps1
```

方式二：使用项目脚本一键运行并生成报告：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Live
```

只运行指定标记：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Live -Marker "smoke"
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Live -Marker "negative"
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Live -Marker "boundary"
```

## 查看 Allure 报告

启动本地静态服务：

```powershell
python -m http.server 8088 --directory reports
python3 -m http.server 8088 --directory reports
```

浏览器访问：

```text
http://127.0.0.1:8088/allure-report/index.html
```

注意：

- 修改用例或测试数据后，需要重新运行 pytest。
- pytest 结束后会自动重新生成 `reports/allure-report`。
- 浏览器只是展示已经生成好的静态报告，不会自动根据代码变化刷新。
- 如果页面看起来没变化，可以强制刷新浏览器，或者重新打开报告地址。

## Allure 报告内容说明

报告中会展示：

- 用例标题：读取 `data/test_data/*.yaml` 中每条 case 的 `title`
- 功能套件：在 `tests/conftest.py` 的 `SUITE_NAMES` 中维护
- 入参信息：Allure 附件 `Case input`
- 预期结果：Allure 附件 `Expected result`
- HTTP 请求：Allure 附件 `HTTP request`
- HTTP 响应：Allure 附件 `HTTP response`
- 失败原因：Allure 附件 `Failure reason`

如果新增测试文件，希望 Allure 显示中文套件名，需要在 `tests/conftest.py` 中补充：

```python
SUITE_NAMES = {
    "test_voice.py": "语音克隆与合成接口",
    "test_videots.py": "字幕翻译接口",
    "test_speaker_classify.py": "说话人分类接口",
}
```

## 测试数据说明

测试数据集中在：

```text
data/test_data/*.yaml
```

常见字段含义：

```yaml
id: 用例编号，用于 pytest 参数名和报告展示
title: 用例标题，会显示到 Allure 报告
category: 用例分类，例如 positive、negative、boundary、flow
request: 请求数据
expected: 预期结果
http_status: 预期 HTTP 状态码
http_status_any: 允许多个 HTTP 状态码
code: 预期业务 code
code_any: 允许多个业务 code
message_contains: 响应信息需要包含的文本
message_contains_any: 响应信息命中任意一个文本即可
json_path_required: 指定 JSON 路径必须存在且非空
```

`http_status_any` 适合接口行为还没完全统一的场景。例如有些反向用例 HTTP 仍然返回 `200`，但业务 `code` 返回 `400`，这时可以用业务 code 判断失败原因。

## 接口关联数据

部分接口需要先提交任务，再查询状态。项目里已经支持一些运行时缓存：

```text
语音克隆提交
  -> 缓存 request_id
  -> 语音合成 speaker_id 使用缓存值

字幕翻译提交
  -> 缓存 task_id
  -> 字幕翻译状态查询使用缓存值

说话人分类提交
  -> 缓存 request_id
  -> 说话人分类状态查询使用缓存值
```

如果状态查询用例直接单独运行，没有前置提交用例，代码会尽量自动提交一次任务并拿到对应 ID。

## Mock 文件说明

文件路径统一维护在 `data/test_data/files.yaml` 的 `files` 区域。

契约测试 `test_all_mock_files_exist` 会检查这些路径是否真实存在。如果报：

```text
Missing mock file for xxx
```

说明 `data/test_data/files.yaml` 中配置了某个文件路径，但 `data/mock_files/` 下面没有这个文件。

处理方式：

- 补上对应 mock 文件
- 或者把 YAML 中的路径改成真实存在的文件

## OpenAPI / Apifox 契约检查

配置文件：

```text
config/openapi_sources.yaml
```

常用命令：

```powershell
python scripts/sync_openapi.py
python3 scripts/sync_openapi.py
```

第一次建立或主动接受新基线：

```powershell
python scripts/sync_openapi.py --update-snapshot
python3 scripts/sync_openapi.py --update-snapshot
```

通过 pytest 运行 OpenAPI 契约检查：

```powershell
python -m pytest tests/test_openapi_contract.py --live
python3 -m pytest tests/test_openapi_contract.py --live
```

生成文件：

```text
data/openapi/apifox_raw.json       从 Apifox 拉到的原始 OpenAPI 文档
data/openapi/apifox_latest.json    最新规范化快照
data/openapi/apifox_snapshot.json  本地基线快照
reports/openapi/apifox_diff.json   机器可读 diff
reports/openapi/apifox_diff.md     人可读 diff 报告
```

如果报：

```text
OpenAPI document root must be an object
```

说明 Apifox 地址返回的不是标准 OpenAPI JSON，可能是 HTML、错误信息、数组或空内容。

如果报：

```text
has_breaking_changes
```

说明最新 OpenAPI 和本地基线相比有破坏性变更，例如：

- 接口被删除
- 参数从非必填变成必填
- 参数类型变化
- 请求体从非必填变成必填
- 成功响应码被删除

可以查看：

```text
reports/openapi/apifox_diff.md
```

确认变更是否合理。如果变更合理，再执行 `--update-snapshot` 接受新的基线。


Allure 报告是前端静态页面，直接双击 `index.html` 可能出现 404、500 或资源加载失败。  
用 `http.server` 可以像正常网站一样访问报告。
