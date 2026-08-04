"""
背景音与人声分离接口测试。

覆盖接口：
- POST /open/voice/separate         提交背景音与人声分离任务

测试数据来源：data/test_data/*.yaml 中 voice_separate 模块
"""

from __future__ import annotations

from typing import Any

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import response_json

from .helpers import assert_case, case_ids, case_params, rendered

def pytest_generate_tests(metafunc):
    """动态参数化：根据 voice_separate 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    if "voice_separate_submit_case" in metafunc.fixturenames:
        cases = load_test_data()["voice_separate"]["submit_cases"]
        metafunc.parametrize("voice_separate_submit_case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_voice_separate_submit(api_client, test_data, common, voice_separate_submit_case, runtime_context):
    """[Live 测试] 提交背景音与人声分离任务。"""
    case = rendered(voice_separate_submit_case, common)
    bundle = build_files(test_data, case.get("files", {}))
    with bundle as files:
        response = api_client.voice_separate(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") in {"positive", "boundary"} and payload:
        task_id = _first_present(payload, ( "data.task_id", "task_id"))
        if task_id:
            runtime_context["voice_separate_task_id"] = str(task_id)
def _submit_voice_separate_and_get_task_id(api_client, test_data):
    """提交一次任务，返回统一任务状态查询所需 task_id。"""
    bundle = build_files(test_data, {"audio": "valid_audio", "srt": "valid_subtitle"})
    with bundle as files:
        response = api_client.voice_separate(files=files, auth="default")
    payload = response_json(response)
    task_id = _first_present(payload, ( "data.task_id", "taskId", "task_id"))
    assert task_id, f"背景音与人声分离提交接口未返回 task_id，无法用于统一状态查询。响应: {payload!r}"
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
