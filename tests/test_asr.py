"""
ASR 语音识别接口测试。

覆盖接口：
- POST /open/asr ASR 语音识别（REST 模式）

测试数据来源：data/test_data/test_asr.yaml 中 asr 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 asr 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()
    mapping = {
        "asr_case": data["asr"]["rest_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_asr_rest(api_client, test_data, common, asr_case):
    """[Live 测试] ASR 语音识别接口（REST 模式）。"""
    case = rendered(asr_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.asr_rest(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    assert_case(response, case)
