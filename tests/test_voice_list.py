"""
公共音色列表查询接口测试。

覆盖接口：
- GET /open/voice/list  公共音色列表查询

测试数据来源：data/test_data/*.yaml 中 voice_list 模块
"""

from __future__ import annotations

from typing import Any

import pytest

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 voice_list 模块数据自动生成测试用例。"""
    if "voice_list_case" in metafunc.fixturenames:
        from openapi_automation.core.config import load_test_data

        cases = load_test_data()["voice_list"]["cases"]
        metafunc.parametrize("voice_list_case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_public_voice_list(api_client, common, voice_list_case):
    """[Live 测试] 公共音色列表查询接口。

    接口：GET /open/voice/list
    请求方式：query params（name / page_no / page_size）
    认证：api_key 请求头
    功能：查询公共音色列表，支持名称模糊匹配和分页。
    """
    case = rendered(voice_list_case, common)
    response = api_client.public_voice_list(params=case.get("params", {}), auth=case.get("auth", "default"))
    payload = assert_case(response, case)

    if _is_success_response(payload):
        _assert_voice_list_payload(payload, case)


def _is_success_response(payload: dict[str, Any] | None) -> bool:
    return bool(payload and payload.get("code") == 200 and isinstance(payload.get("data"), dict))


def _assert_voice_list_payload(payload: dict[str, Any], case: dict[str, Any]) -> None:
    data = payload["data"]
    assert "list" in data and isinstance(data["list"], list), payload
    assert "total" in data and isinstance(data["total"], int), payload
    assert data["total"] >= 0, payload

    params = case.get("params") or {}
    page_size = params.get("page_size")
    if isinstance(page_size, int) and page_size > 0:
        assert len(data["list"]) <= page_size, payload

    if case.get("expected_empty_result"):
        assert data["list"] == [], payload
        assert data["total"] == 0, payload

    for item in data["list"]:
        _assert_voice_item(item)


def _assert_voice_item(item: Any) -> None:
    assert isinstance(item, dict), item
    for field in ("name", "description", "lang_code", "is_public", "created_at", "audio_url"):
        assert field in item, item
    assert isinstance(item["name"], str) and item["name"].strip(), item
    assert item["description"] is None or isinstance(item["description"], str), item
    assert item["lang_code"] is None or isinstance(item["lang_code"], str), item
    assert item["is_public"] is True, item
    assert isinstance(item["created_at"], str) and item["created_at"].strip(), item
    assert isinstance(item["audio_url"], str) and item["audio_url"].strip(), item
