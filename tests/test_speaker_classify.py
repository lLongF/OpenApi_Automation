"""
说话人分类接口测试。

覆盖接口：
- POST /open/speaker-classify/submit  说话人分类任务提交

测试数据来源：data/test_data/*.yaml 中 speaker_classify 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import response_json

from .helpers import assert_case, case_ids, case_params, rendered

def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data/*.yaml 中 speaker_classify 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    if "speaker_submit_case" in metafunc.fixturenames:
        cases = load_test_data()["speaker_classify"]["submit_cases"]
        metafunc.parametrize("speaker_submit_case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_speaker_classify_submit(api_client, test_data, common, speaker_submit_case, runtime_context):
    """[Live 测试] 说话人分类任务提交接口。

    接口：POST /open/speaker-classify/submit
    请求方式：multipart/form-data（音频文件）
    认证：api_key 请求头
    正向用例成功后缓存 request_id，供统一任务状态查询接口使用。
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

def _submit_speaker_classify_and_get_request_id(api_client, test_data):
    """提交一次说话人分类任务，返回统一任务状态查询所需 request_id。"""
    bundle = build_files(test_data, {"file": "valid_audio"})
    with bundle as files:
        response = api_client.speaker_classify_submit(files=files, auth="default")
    payload = response_json(response)
    request_id = (payload.get("data") or {}).get("request_id") or payload.get("request_id")
    assert request_id, f"说话人分类提交接口未返回 request_id，无法用于统一状态查询。响应: {payload!r}"
    return str(request_id)
