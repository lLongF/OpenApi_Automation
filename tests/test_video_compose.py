"""
视频压制合成接口测试。

覆盖接口：
- POST /open/video-compose/tasks   提交视频压制合成任务

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

    if "video_compose_submit_case" in metafunc.fixturenames:
        cases = load_test_data()["video_compose"]["submit_cases"]
        metafunc.parametrize("video_compose_submit_case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_video_compose_submit(api_client, test_data, common, video_compose_submit_case, runtime_context, env_config):
    """[Live 测试] 提交视频压制合成任务。"""
    case = rendered(video_compose_submit_case, common)
    only_envs = case.get("only_envs")
    if only_envs and env_config.name not in only_envs:
        pytest.skip(
            f"{case['id']} only runs in {only_envs}; current environment: {env_config.name}"
        )
    bundle = build_files(test_data, case.get("files", {}))
    with bundle as files:
        response = api_client.video_compose(
            files=files or None,
            params=case.get("params"),
            auth=case.get("auth", "default"),
            streaming_upload=case.get("streaming_upload", False),
        )
    payload = assert_case(response, case)
    if case.get("category") in {"positive", "boundary"} and payload:
        task_id = _first_present(payload, ("data.taskId", "data.task_id", "taskId", "task_id"))
        if task_id:
            runtime_context["video_compose_task_id"] = str(task_id)
def _submit_video_compose_and_get_task_id(api_client, test_data):
    """提交一次任务，返回统一任务状态查询所需 task_id。"""
    bundle = build_files(test_data, {"video_file": "valid_video", "audio_file": "valid_audio", "subtitle_file": "valid_subtitle"})
    with bundle as files:
        response = api_client.video_compose(
            files=files,
            params={
                "target_language": "zh",
                "subtitle_font_size": 24,
                "subtitle_x": 80,
                "subtitle_y": 950,
                "coordinate_width": 1920,
                "coordinate_height": 1080,
            },
            auth="default",
        )
    payload = response_json(response)
    task_id = _first_present(payload, ("data.taskId", "data.task_id", "taskId", "task_id"))
    assert task_id, f"视频压制合成提交接口未返回 task_id，无法用于统一状态查询。响应: {payload!r}"
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
