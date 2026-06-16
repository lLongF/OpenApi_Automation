"""
字幕擦除 / ASR 语音识别 / 说话人分类 接口测试。

覆盖接口：
- POST /open/subtitle/erase       字幕擦除提交
- GET  /open/subtitle/erase/result 字幕擦除结果查询
- POST /open/asr                   ASR 语音识别（REST 模式）
- POST /open/speaker-classify/submit  说话人分类提交
- GET  /open/speaker-classify/status  说话人分类状态查询

测试数据来源：data/test_data.yaml 中 subtitle_erase / asr / speaker_classify 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data.yaml 中的数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()
    mapping = {
        "erase_submit_case": data["subtitle_erase"]["submit_cases"],
        "erase_result_case": data["subtitle_erase"]["result_cases"],
        "asr_case": data["asr"]["rest_cases"],
        "speaker_submit_case": data["speaker_classify"]["submit_cases"],
        "speaker_status_case": data["speaker_classify"]["status_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_subtitle_erase_submit(api_client, test_data, common, erase_submit_case):
    """[Live 测试] 字幕擦除提交接口。

    接口：POST /open/subtitle/erase
    请求方式：multipart/form-data（音频文件 + 表单参数）
    认证：api_key 请求头
    """
    case = rendered(erase_submit_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.erase_subtitle(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    assert_case(response, case)


@pytest.mark.live
def test_subtitle_erase_result(api_client, common, erase_result_case):
    """[Live 测试] 字幕擦除结果查询接口。

    接口：GET /open/subtitle/erase/result
    请求参数：task_id（查询参数）
    认证：api_key 请求头
    """
    case = rendered(erase_result_case, common)
    response = api_client.erase_result(params=case.get("params", {}), auth=case.get("auth", "default"))
    assert_case(response, case)


@pytest.mark.live
def test_asr_rest(api_client, test_data, common, asr_case):
    """[Live 测试] ASR 语音识别接口（REST 模式）。

    接口：POST /open/asr
    请求方式：multipart/form-data（音频文件 + 表单参数如 language）
    认证：api_key 请求头
    """
    case = rendered(asr_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.asr_rest(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    assert_case(response, case)


@pytest.mark.live
def test_speaker_classify_submit(api_client, test_data, common, speaker_submit_case):
    """[Live 测试] 说话人分类任务提交接口。

    接口：POST /open/speaker-classify/submit
    请求方式：multipart/form-data（音频文件）
    认证：api_key 请求头
    """
    case = rendered(speaker_submit_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.speaker_classify_submit(files=files or None, auth=case.get("auth", "default"))
    assert_case(response, case)


@pytest.mark.live
def test_speaker_classify_status(api_client, common, speaker_status_case):
    """[Live 测试] 说话人分类任务状态查询接口。

    接口：GET /open/speaker-classify/status
    请求参数：task_id（查询参数）
    认证：api_key 请求头
    """
    case = rendered(speaker_status_case, common)
    response = api_client.speaker_classify_status(params=case.get("params", {}), auth=case.get("auth", "default"))
    assert_case(response, case)
