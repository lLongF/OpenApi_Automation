"""
视频压制合成接口测试。

覆盖接口：
- POST /open/video-compose/tasks   提交视频压制合成任务
- GET  /open/video-compose/status  查询视频压制合成任务状态

测试数据来源：data/test_data/*.yaml 中 video_compose 模块
"""

from __future__ import annotations

from typing import Any

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import response_json

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 video_compose 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()["video_compose"]
    mapping = {
        "video_compose_submit_case": data["submit_cases"],
        "video_compose_status_case": data["status_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_video_compose_submit(api_client, test_data, common, video_compose_submit_case, runtime_context):
    """[Live 测试] 提交视频压制合成任务。"""
    case = rendered(video_compose_submit_case, common)
    bundle = build_files(test_data, case.get("files", {}))
    with bundle as files:
        response = api_client.video_compose(files=files or None, params=case.get("params"), auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") in {"positive", "boundary"} and payload:
        task_id = _first_present(payload, ("data.taskId", "data.task_id", "taskId", "task_id"))
        if task_id:
            runtime_context["video_compose_task_id"] = str(task_id)


@pytest.mark.live
def test_video_compose_status(api_client, test_data, common, video_compose_status_case, runtime_context):
    """[Live 测试] 查询视频压制合成任务状态。"""
    case = rendered(video_compose_status_case, common)
    case = _resolve_auto_video_compose_task_id(case, api_client, test_data, runtime_context)
    response = api_client.video_compose_status(params=case.get("params", {}), auth=case.get("auth", "default"))
    assert_case(response, case)


def _resolve_auto_video_compose_task_id(case, api_client, test_data, runtime_context):
    params = case.get("params")
    if not isinstance(params, dict):
        return case
    task_id = params.get("task_id")
    if not task_id or not str(task_id).startswith("replace-with-valid"):
        return case

    resolved = dict(case)
    resolved_params = dict(params)
    context_task_id = runtime_context.get("video_compose_task_id")
    resolved_params["task_id"] = context_task_id or _submit_video_compose_and_get_task_id(api_client, test_data)
    resolved["params"] = resolved_params
    return resolved


def _submit_video_compose_and_get_task_id(api_client, test_data):
    bundle = build_files(test_data, {"video_file": "valid_video", "audio_file": "valid_audio", "subtitle_file": "valid_subtitle"})
    with bundle as files:
        response = api_client.video_compose(
            files=files,
            params={
                "target_language": "zh",
                "subtitle_font_size": 24,
                "coordinate_width": 1920,
                "coordinate_height": 1080,
            },
            auth="default",
        )
    payload = response_json(response)
    task_id = _first_present(payload, ("data.taskId", "data.task_id", "taskId", "task_id"))
    assert task_id, f"视频压制合成提交接口未返回 task_id，无法用于状态查询。响应: {payload!r}"
    return str(task_id)


def _first_present(payload: dict[str, Any], paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current not in (None, ""):
            return current
    return None
