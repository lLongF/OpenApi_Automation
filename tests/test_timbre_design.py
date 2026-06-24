"""
音色设计（Timbre Design）接口测试。

覆盖接口：
- POST /open/timbre-design/generate  音色设计生成
- GET /open/timbre-design/status     音色设计状态查询

测试数据来源：data/test_data/*.yaml 中 timbre_design 模块
"""

from __future__ import annotations

import pytest

from .helpers import assert_case, case_ids, case_params, rendered
from openapi_automation.core.assertions import response_json


def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data/*.yaml 中 timbre_design 模块数据自动生成测试用例。"""
    if "case" in metafunc.fixturenames:
        from openapi_automation.core.config import load_test_data

        cases = load_test_data()["timbre_design"]["cases"]
        metafunc.parametrize("case", case_params(cases), ids=case_ids(cases))
    if "status_case" in metafunc.fixturenames:
        from openapi_automation.core.config import load_test_data

        cases = load_test_data()["timbre_design"]["status_cases"]
        metafunc.parametrize("status_case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_timbre_design(api_client, common, case, runtime_context):
    """[Live 测试] 音色设计生成接口。

    接口：POST /open/timbre-design/generate
    请求方式：application/json（JSON 请求体，包含 prompt / num / timbre_id 等参数）
    认证：api_key 请求头
    功能：根据文本描述（prompt）生成特定音色的音频
    """
    case = rendered(case, common)
    response = api_client.generate_timbre(json=case["json"], auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") == "positive" and payload:
        request_id = payload.get("request_id") or payload.get("requestId") or (payload.get("data") or {}).get("request_id")
        if request_id:
            runtime_context["timbre_request_id"] = str(request_id)


@pytest.mark.live
def test_timbre_status(api_client, test_data, common, status_case, runtime_context):
    """[Live 测试] 音色设计状态查询接口。

    接口：GET /open/timbre-design/status
    依赖：上游 /open/timbre-design/generate 返回的 request_id
    """
    case = rendered(status_case, common)
    params = dict(case.get("params", {}))
    request_id = params.get("request_id")
    if request_id and str(request_id).startswith("replace-with-valid"):
        params["request_id"] = runtime_context.get("timbre_request_id") or _generate_timbre_and_get_request_id(api_client, test_data)
    response = api_client.timbre_status(params=params, auth=case.get("auth", "default"))
    assert_case(response, {**case, "params": params})


def _generate_timbre_and_get_request_id(api_client, test_data) -> str:
    for item in test_data["timbre_design"]["cases"]:
        if item.get("category") == "positive":
            response = api_client.generate_timbre(json=item["json"])
            payload = response_json(response)
            request_id = payload.get("request_id") or payload.get("requestId") or (payload.get("data") or {}).get("request_id")
            assert request_id, f"音色设计接口未返回 request_id/requestId，无法查询状态。响应: {payload!r}"
            return str(request_id)
    raise AssertionError("未找到音色设计正向用例，无法自动生成 request_id。")
