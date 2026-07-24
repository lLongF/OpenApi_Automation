"""
字幕擦除接口测试。

覆盖接口：
- POST /open/subtitle/erase        字幕擦除提交
- GET  /open/subtitle/erase/result 字幕擦除结果查询

测试数据来源：data/test_data/test_subtitle_erase.yaml 中 subtitle_erase 模块
"""

from __future__ import annotations

import time

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import response_json

from .helpers import assert_case, case_ids, case_params, rendered

SUBTITLE_ERASE_POLL_INTERVAL_SECONDS = 5
SUBTITLE_ERASE_POLL_TIMEOUT_SECONDS = 360


def pytest_generate_tests(metafunc):
    """动态参数化：根据 subtitle_erase 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()
    mapping = {
        "erase_submit_case": data["subtitle_erase"]["submit_cases"],
        "erase_result_case": data["subtitle_erase"]["result_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_subtitle_erase_submit(api_client, test_data, common, erase_submit_case, runtime_context):
    """[Live 测试] 字幕擦除任务提交接口。"""
    case = rendered(erase_submit_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.erase_subtitle(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") == "positive" and payload:
        data = payload.get("data") or {}
        project_id = data.get("project_id") or payload.get("project_id")
        if project_id:
            runtime_context["project_id"] = str(project_id)
        task_id = data.get("task_id") or data.get("taskId") or payload.get("task_id") or payload.get("taskId")
        if task_id:
            runtime_context["subtitle_erase_task_id"] = str(task_id)


@pytest.mark.live
def test_subtitle_erase_result(api_client, common, erase_result_case, runtime_context, test_data):
    """[Live 测试] 字幕擦除结果查询接口。"""
    case = rendered(erase_result_case, common)
    case = resolve_auto_project_id(case, api_client, test_data, runtime_context)
    if case.get("id") == "SER_POS_001":
        response = poll_subtitle_erase_success(api_client, case)
        payload = assert_case(response, case)
        status = ((payload or {}).get("data") or {}).get("status")
        assert status == "success", payload
        return

    response = api_client.erase_result(params=case.get("params", {}), auth=case.get("auth", "default"))
    assert_case(response, case)


def resolve_auto_project_id(case, api_client, test_data, runtime_context):
    params = case.get("params")
    if not isinstance(params, dict):
        return case

    project_id = params.get("project_id")
    if not project_id or not str(project_id).startswith("replace-with-valid"):
        return case

    resolved = dict(case)
    resolved_params = dict(params)

    context_project_id = runtime_context.get("project_id")
    resolved_params["project_id"] = context_project_id or submit_subtitle_erase_and_get_project_id(api_client, test_data)

    resolved["params"] = resolved_params
    return resolved


def submit_subtitle_erase_and_get_project_id(api_client, test_data):
    bundle = build_files(test_data, {"file": "valid_video"})
    with bundle as files:
        response = api_client.erase_subtitle(
            files=files,
            data={
                "name": "api-auto-erase",
                "language_code": "zh",
                "subtitle_mode": 0,
                "do_not_encrypt_link": "true",
            },
        )

    payload = response_json(response)
    project_id = (payload.get("data") or {}).get("project_id") or payload.get("project_id")

    assert project_id, f"字幕擦除提交接口未返回 project_id，无法用于结果查询。响应: {payload!r}"
    return str(project_id)


def poll_subtitle_erase_success(api_client, case):
    """Poll subtitle erase result until the async task succeeds."""
    deadline = time.monotonic() + SUBTITLE_ERASE_POLL_TIMEOUT_SECONDS
    last_payload = None

    while True:
        response = api_client.erase_result(params=case.get("params", {}), auth=case.get("auth", "default"))
        last_payload = response_json(response)
        status = (last_payload.get("data") or {}).get("status")
        if response.status_code == 200 and status == "success":
            return response
        if time.monotonic() >= deadline:
            break
        time.sleep(SUBTITLE_ERASE_POLL_INTERVAL_SECONDS)

    raise AssertionError(
        "字幕擦除结果查询未在 "
        f"{SUBTITLE_ERASE_POLL_TIMEOUT_SECONDS}s 内返回 success，最后响应: {last_payload!r}"
    )
