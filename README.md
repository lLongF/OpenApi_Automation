# OpenAPI 接口自动化

基于 `pytest` 的 OpenAPI 接口自动化测试项目，覆盖语音克隆、语音合成、个人音色管理、MIMO 音色设计、字幕翻译、视频字幕/ASR、说话人分类、OpenAPI 契约检查等接口。

项目提供两种使用方式：

- Web 控制台：适合日常点选环境、模块并查看执行记录和 Allure 报告。
- 命令行：适合本地调试、CI 或精确运行某个测试文件/用例。

## 快速使用

第一次使用先安装依赖：

```powershell
cd D:\Project\OpenApi_Automation
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts/install_allure.ps1
```

运行真实接口用例并生成报告：

```powershell
python -m pytest tests --live --clean-alluredir
powershell -ExecutionPolicy Bypass -File scripts/generate_allure_report.ps1
```

常用报告位置：

```text
reports/report.html
reports/allure-report/index.html
```

只跑本地契约和数据校验：

```powershell
python -m pytest tests/test_contract_data.py --no-allure-report
```

启动 Web 控制台：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_web.ps1 -Port 8000
```

打开：

```text
http://127.0.0.1:8088/allure-report
```

## 上传文件与测试数据要求

上传文件统一放在 `data/mock_files/`，并在 `data/test_data/files.yaml` 里维护 `file_key -> 文件路径`。接口用例只引用 `file_key`，不用直接写文件路径。

| 接口 | 需要的文件 | 格式/大小/时长要求 | 当前测试数据 file_key |
| --- | --- | --- | --- |
| 语音克隆 `/open/voice/zeroshot/clone` | 音频 | mp3/wav/m4a；1s-30s；不超过 10MB | `valid_clone_audio` 约 0.61MB/19.9s；`valid_clone_open_audio` 约 14.80MB/20.2s；`valid_clone_1min_5mb` 约 5.85MB/2.1min；`empty_audio`；`valid_video` 用于格式错误 |
| 语音合成 `/open/voice/zeroshot/infer` | 可选参考音频 + 文本 | 音频 1s-30s、不超过 10MB；文本不超过 3000 字符 | `valid_clone_audio`；`valid_clone_1min_5mb`；`valid_clone_open_audio` |
| 公共音色列表 `/open/voice/list` | 无文件 | 只使用 query 参数 `name/page_no/page_size` | 无 |
| 个人音色保存/查询/更新/删除 `/open/voice/zeroshot/save`、`/open/voice/user-voices/*` | 克隆请求 ID 或无文件 | 保存需要克隆 `request_id` 和个人音色属性；查询支持分页与属性筛选 | 克隆时使用 `valid_clone_audio` |
| MIMO 音色设计 `/open/timbre-design/generate-mimo` | 无文件 | JSON 参数 `text`、`description`、`optimize_text` | 无 |
| 字幕翻译/重译/回译 `/open/videots/*` | 字幕文件 | srt；不超过 1MB | `valid_subtitle`；`valid_subtitle_translated`；`empty_subtitle`；`invalid_subtitle`；`oversize_subtitle_11mb` 约 10.49MB |
| 字幕擦除 `/open/subtitle/erase` | 视频 | mp4/mov；10s-60min；不超过 2GB | `valid_video` 约 1.30MB/20.2s；`invalid_video`；`empty_video` |
| 语音识别 `/open/asr` | 音频 | mp3/wav/m4a；10s-60min；不超过 100MB | `valid_audio` 约 0.61MB/19.9s；`valid_speaker_5min_50mb` 约 50MB/5min；`oversize_speaker_12min` 约 10.99MB/12min；`valid_audio_65min` 约 14.88MB/65min；`valid_audio_205MB` 约 205MB；`invalid_audio`；`empty_audio` |
| 说话人分类 `/open/speaker-classify/submit` | 音频 | wav/mp3/m4a；不超过 10min；不超过 50MB | `valid_audio`；`oversize_speaker_51mb` 约 52MB/5min；`oversize_speaker_12min` 约 12min；`valid_video` 用于格式错误；`empty_audio` |
| 背景音与人声分离 `/open/voice/separate` | 音频，字幕可选 | 音频 wav/mp3/m4a、不超过 10min、不超过 50MB；字幕 srt、不超过 1MB | `valid_audio`；`valid_subtitle`；`valid_speaker_5min_50mb`；`oversize_speaker_51mb`；`oversize_speaker_12min`；`oversize_subtitle_11mb`；`invalid_audio`；`invalid_subtitle`；`empty_audio` |
| 视频压制合成 `/open/video-compose/tasks` | 视频必填，音频/字幕可选 | 视频 mp4/mov、10s-60min、不超过 2GB；音频不超过 10min/50MB；字幕 srt、不超过 1MB | `valid_video`；`valid_compose_video` 约 14.87MB/3min；`valid_audio`；`valid_subtitle`；`empty_video`；`invalid_video`；`invalid_audio`；`invalid_subtitle`；`oversize_speaker_51mb`；`oversize_speaker_12min`；`oversize_subtitle_11mb` |

测试数据文件对应关系：

```text
data/test_data/test_voice_clone.yaml        语音克隆
data/test_data/test_voice_infer.yaml        语音合成
data/test_data/test_voice_list.yaml         公共音色列表
data/test_data/test_user_voices.yaml        个人音色保存/查询/更新/删除
data/test_data/test_timbre_design_mimo.yaml MIMO 音色设计
data/test_data/test_videots.yaml            字幕翻译/重译/回译
data/test_data/test_subtitle_erase.yaml     字幕擦除
data/test_data/test_asr.yaml                语音识别
data/test_data/test_speaker_classify.yaml   说话人分类
data/test_data/test_voice_separate.yaml     背景音与人声分离
data/test_data/test_video_compose.yaml      视频压制合成
```

新增或替换文件时，只需要两步：

1. 把文件放入 `data/mock_files/`。
2. 在 `data/test_data/files.yaml` 增加或修改对应 `file_key`，再在业务 YAML 用例中引用它。

## 目录说明

```text
config/
  env.yaml                    默认环境及环境配置目录
  environments/
    dev.yaml                  开发环境非敏感配置
    test.yaml                 测试环境非敏感配置
    prod.yaml                 生产环境非敏感配置
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
