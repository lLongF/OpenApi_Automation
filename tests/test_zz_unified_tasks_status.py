"""统一任务状态查询接口测试。"""

from __future__ import annotations

import time

import pytest

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    if "task_status_case" in metafunc.fixturenames:
        from openapi_automation.core.config import load_test_data

        cases = load_test_data()["tasks_status"]["cases"]
        metafunc.parametrize("task_status_case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_unified_task_status(api_client, common, test_data, task_status_case, runtime_context):
    """[Live 测试] GET /open/tasks/status，按 type 与 task_id 查询异步任务。"""
    case = rendered(task_status_case, common)
    params = dict(case.get("params") or {})
    if case.get("category") == "positive":
        params = {"type": case["type"], "task_id": _task_id(case, runtime_context, api_client, test_data)}
        response = _poll_until_final(api_client, params, test_data["tasks_status"])
        payload = assert_case(response, case)
        data = (payload or {}).get("data") or {}
        assert data.get("task_id") == params["task_id"], payload
        assert data.get("status") == case["expected"]["final_status"], payload
        return

    response = api_client.task_status(params=params, auth=case.get("auth", "default"))
    assert_case(response, case)


def _task_id(case, runtime_context, api_client, test_data) -> str:
    task_id = runtime_context.get(case["context_key"])
    if task_id:
        return str(task_id)

    task_id = _submit_task_for_unified_status(case["type"], api_client, test_data)
    runtime_context[case["context_key"]] = str(task_id)
    return str(task_id)


def _submit_task_for_unified_status(task_type, api_client, test_data) -> str:
    """单独执行统一查询用例时，补提交一个对应的正向任务。"""
    if task_type == "subtitle_translation":
        from .test_videots import submit_translation_and_get_task_id

        return submit_translation_and_get_task_id(api_client, test_data)
    if task_type == "video_compose":
        from .test_video_compose import _submit_video_compose_and_get_task_id

        return _submit_video_compose_and_get_task_id(api_client, test_data)
    if task_type == "voice_separate":
        from .test_voice_separate import _submit_voice_separate_and_get_task_id

        return _submit_voice_separate_and_get_task_id(api_client, test_data)
    if task_type == "speaker_classify":
        from .test_speaker_classify import _submit_speaker_classify_and_get_request_id

        return _submit_speaker_classify_and_get_request_id(api_client, test_data)
    if task_type == "timbre_design":
        from .test_timbre_design import _generate_timbre_and_get_request_id

        return _generate_timbre_and_get_request_id(api_client, test_data)
    if task_type == "subtitle_erase":
        from openapi_automation.clients.openapi_client import build_files
        from openapi_automation.core.assertions import response_json

        bundle = build_files(test_data, {"file": "valid_video"})
        with bundle as files:
            response = api_client.erase_subtitle(
                files=files,
                data={"name": "api-auto-unified-status", "language_code": "zh", "subtitle_mode": 0},
            )
        payload = response_json(response)
        data = payload.get("data") or {}
        task_id = data.get("task_id") or data.get("taskId") or payload.get("task_id") or payload.get("taskId")
        assert task_id, f"字幕擦除提交接口未返回 task_id，无法用于统一状态查询。响应: {payload!r}"
        return str(task_id)
    raise AssertionError(f"Unsupported unified task type: {task_type}")


def _poll_until_final(api_client, params, settings):
    interval = float(settings["poll_interval_seconds"])
    deadline = time.monotonic() + float(settings["poll_timeout_seconds"])
    last_response = None
    while time.monotonic() <= deadline:
        response = api_client.task_status(params=params)
        last_response = response
        try:
            payload = response.json()
        except ValueError:
            return response
        status = ((payload.get("data") or {}).get("status") if isinstance(payload, dict) else None)
        if status in {"completed", "failed"}:
            return response
        time.sleep(interval)
    assert last_response is not None
    return last_response
