"""
说话人分类接口测试。

覆盖接口：
- POST /open/speaker-classify/submit  说话人分类任务提交
- GET  /open/speaker-classify/status  说话人分类状态查询

测试数据来源：data/test_data/*.yaml 中 speaker_classify 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data/*.yaml 中 speaker_classify 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()["speaker_classify"]
    mapping = {
        "speaker_submit_case": data["submit_cases"],
        "speaker_status_case": data["status_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_speaker_classify_submit(api_client, test_data, common, speaker_submit_case, runtime_context):
    """[Live 测试] 说话人分类任务提交接口。

    接口：POST /open/speaker-classify/submit
    请求方式：multipart/form-data（音频文件）
    认证：api_key 请求头
    正向用例成功后缓存 request_id，供状态查询接口使用。
    """
    case = rendered(speaker_submit_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.speaker_classify_submit(files=files or None, auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") == "positive" and payload:
        request_id = (payload.get("data") or {}).get("request_id") or payload.get("request_id")
        if request_id:
            runtime_context["speaker_classify_request_id"] = str(request_id)


@pytest.mark.live
def test_speaker_classify_status(api_client, test_data, common, speaker_status_case, runtime_context):
    """[Live 测试] 说话人分类任务状态查询接口。

    接口：GET /open/speaker-classify/status
    请求参数：request_id（查询参数）
    认证：api_key 请求头
    如果 request_id 仍为占位值，会优先使用提交接口缓存的 request_id；单独运行时会自动补跑一次提交接口。
    """
    case = rendered(speaker_status_case, common)
    case = _resolve_auto_speaker_classify_request_id(case, api_client, test_data, runtime_context)
    response = api_client.speaker_classify_status(params=case.get("params", {}), auth=case.get("auth", "default"))
    assert_case(response, case)


def _resolve_auto_speaker_classify_request_id(case, api_client, test_data, runtime_context):
    """把状态查询用例中的占位 request_id 替换成真实值。"""
    params = case.get("params")
    if not isinstance(params, dict):
        return case
    request_id = params.get("request_id")
    if not request_id or not str(request_id).startswith("replace-with-valid"):
        return case

    resolved = dict(case)
    resolved_params = dict(params)
    context_request_id = runtime_context.get("speaker_classify_request_id")
    resolved_params["request_id"] = context_request_id or _submit_speaker_classify_and_get_request_id(api_client, test_data)
    resolved["params"] = resolved_params
    return resolved


def _submit_speaker_classify_and_get_request_id(api_client, test_data):
    """提交一次说话人分类任务，返回状态查询所需 request_id。"""
    bundle = build_files(test_data, {"file": "valid_audio"})
    with bundle as files:
        response = api_client.speaker_classify_submit(files=files, auth="default")
    payload = response.json()
    request_id = (payload.get("data") or {}).get("request_id") or payload.get("request_id")
    assert request_id, f"说话人分类提交接口未返回 request_id，无法用于状态查询。响应: {payload!r}"
    return str(request_id)
