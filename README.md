# 山海智影 OpenAPI 接口自动化框架

这是一个面向生产项目的 Python 接口自动化基座，覆盖语音克隆、语音合成、音色设计、字幕翻译、字幕擦除、ASR、公共说话人分类等 REST 接口。当前版本已按要求移除 WebSocket 接口。

## 技术选型

- `pytest`：用例组织、参数化、标记分层，适合接口自动化长期维护。
- `requests`：REST API 调用稳定成熟，封装成本低。
- `PyYAML`：测试数据、环境配置外置，替换后即时生效。
- `pytest-html + allure-pytest`：默认生成 HTML 报告，也支持 Allure 全量报告。
- `jsonschema`：预留响应 schema 校验能力，适合后续把接口契约继续细化。

## 目录说明

```text
config/env.yaml                  环境、域名、超时、重试、user_id/admin_token 配置
config/openapi_sources.yaml      Apifox RAW URL / OpenAPI 同步源配置
data/test_data.yaml              所有接口测试数据，含正向、反向、边界、流程数据
data/mock_files/                 文件类 mock 数据，替换文件即可生效
src/openapi_automation/core/     配置、HTTP、断言、文件、模板渲染等通用能力
src/openapi_automation/clients/  REST 业务 client
tests/                           pytest 用例层，只表达测试意图
reports/                         HTML 与 Allure 结果输出
scripts/run_tests.sh             live 测试运行脚本
scripts/sync_openapi.py          从 Apifox/Swagger 拉取 OpenAPI 并生成变更报告
```

## 运行方式

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

只跑本地 contract 检查，不访问线上接口：

```bash
python3 -m pytest -m contract
```

默认全量运行也不会访问线上接口，所有 `live` 用例会跳过：

```bash
python3 -m pytest
```

运行真实接口测试前，需要配置固定 `user_id`。框架会先调用 `/admin/api-key/create`，从响应 `data.api_key` 取值，再把这个 key 自动放进所有业务接口的 `api_key` header。

```bash
export SHANHAI_USER_ID="你的固定user_id"
export SHANHAI_ADMIN_TOKEN="如果环境需要X-Admin-Token就填写，不需要可不配"
bash scripts/run_tests.sh
```

按标记运行：

```bash
bash scripts/run_tests.sh "smoke"
bash scripts/run_tests.sh "negative or boundary"
```

## Apifox 契约同步

你们公司的 Apifox 项目邀请链接已记录在 `config/openapi_sources.yaml`，它用于人进入项目协作；CI/CD 自动化不能稳定依赖邀请页登录态，所以生产执行需要配置下面两种方式之一。

方式一，推荐：配置 Apifox OpenAPI RAW URL。

当前本地 Apifox RAW URL 已写入配置：

```text
http://127.0.0.1:4523/export/openapi/4?version=3.0
```

如需临时覆盖，可配置：

```bash
export APIFOX_OPENAPI_RAW_URL="Apifox OpenAPI RAW URL"
python3 scripts/sync_openapi.py
```

方式二：使用 Apifox 开放 API。

在 CI/CD 密钥中配置：

```bash
export APIFOX_PROJECT_ID="Apifox 项目 ID"
export APIFOX_ACCESS_TOKEN="Apifox API 访问令牌"
python3 scripts/sync_openapi.py
```

同步后会生成：

```text
data/openapi/apifox_latest.json       最新接口快照
data/openapi/apifox_snapshot.json     基线快照，需手动接受或脚本加 --update-snapshot
reports/openapi/apifox_diff.json      机器可读 diff
reports/openapi/apifox_diff.md        人可读变更报告
```

第一次建立基线：

```bash
python3 scripts/sync_openapi.py --update-snapshot
```

后续后端发布后检查接口变更：

```bash
python3 scripts/sync_openapi.py
```

如果检测到删除接口、参数变必填、参数类型变化、请求体变必填、成功响应被移除等破坏性变更，脚本默认返回非 0，适合接入 Jenkins、GitLab CI、GitHub Actions 或公司发布流水线。

也可以通过 pytest 统一出报告：

```bash
python3 -m pytest -m openapi --live
```

报告位置：

- Pytest HTML：`reports/report.html`
- Allure 原始结果：`reports/allure-results`
- 如果本机安装了 Allure CLI，脚本会生成：`reports/allure-report/index.html`
- Apifox/OpenAPI Diff：`reports/openapi/apifox_diff.md`

## Mock 数据替换

接口测试数据集中在 `data/test_data.yaml`。当前 `speaker_id` 已支持自动链路传递：如果仍是占位值，语音合成测试会先调用语音克隆接口，把返回的 `request_id` 自动作为 `speaker_id` 使用。

```text
语音克隆 /open/voice/zeroshot/clone
  -> response.request_id
  -> 语音合成 /open/voice/zeroshot/infer 的 speaker_id
```

语音克隆和语音合成的链路现在直接在 `tests/test_voice.py` 里完成：`test_voice_clone` 正向用例会缓存 `request_id`，后续 `test_voice_infer` 遇到占位 `speaker_id` 时会优先使用这个缓存值。

可以运行正向用例验证这条链路：

```bash
bash scripts/run_tests.sh "smoke"
```

其他业务依赖 ID 暂时仍可在 `data/test_data.yaml` 手动替换，例如 `task_id`、`project_id`、`request_id`：

```yaml
common:
  task_id: "真实翻译接口返回的 task_id"
  project_id: "真实字幕擦除接口返回的 project_id"
  request_id: "真实说话人识别接口返回的 request_id"
```

文件类数据在 `data/mock_files/`，直接替换同名文件即可。 live 正向测试前建议替换为真实有效文件：

- 语音克隆：音频 1s-30s，最大 10MB
- 语音合成：参考音频 1s-30s，最大 10MB；文本最大 3000 字符
- 音色设计：文本最大 500 字符
- 翻译接口：SRT 字幕文件，最大 1MB
- 字幕擦除：MP4/MOV，10 秒到 60 分钟，最大 2GB
- ASR 识别：mp3/wav/m4a，10 秒到 60 分钟，最大 2GB
- 说话人识别：wav/mp3/m4a，10 分钟内，最大 50MB

## 用例覆盖

当前数据层已按接口测试标准覆盖：

- 正向：成功请求、关键字段断言、业务码断言。
- 反向：缺失文件、文件格式错误、文件超大小、文本为空、文本超长度、任务 ID 缺失。
- 边界：围绕图片里的文件大小、格式、文本长度限制设计。
- 流程：翻译任务、字幕擦除、说话人分类的提交与状态查询。

## 注意事项

文档中部分接口错误码使用 HTTP 200 + 业务 `code`，也有接口使用 400/500。断言层支持 `http_status_any`、`code_any`、`message_contains_any`，便于兼容当前文档和真实服务差异。生产联调稳定后，建议逐步把模糊断言收紧为精确错误码与 schema。

当前 `data/mock_files` 里有若干负向用例文件，例如 `oversize_audio_11mb.wav`、`oversize_video_2100mb.mp4`。这些是稀疏文件，用于触发大小限制，不会实际占满同等磁盘空间。
