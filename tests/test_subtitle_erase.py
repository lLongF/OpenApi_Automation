"""
字幕擦除接口测试。

覆盖接口：
- POST /open/subtitle/erase        字幕擦除提交

测试数据来源：data/test_data/test_subtitle_erase.yaml 中 subtitle_erase 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 subtitle_erase 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()
    if "erase_submit_case" in metafunc.fixturenames:
        cases = data["subtitle_erase"]["submit_cases"]
        metafunc.parametrize("erase_submit_case", case_params(cases), ids=case_ids(cases))


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
