"""MIMO 音色设计接口测试。"""

from __future__ import annotations

import pytest

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """根据 timbre_design_mimo 模块数据自动生成测试用例。"""
    if "case" in metafunc.fixturenames:
        from openapi_automation.core.config import load_test_data

        cases = load_test_data()["timbre_design_mimo"]["cases"]
        metafunc.parametrize("case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_mimo_timbre_design(api_client, common, case):
    """[Live 测试] POST /open/timbre-design/generate-mimo。"""
    case = rendered(case, common)
    response = api_client.generate_mimo_timbre(json=case["json"], auth=case.get("auth", "default"))
    assert_case(response, case)
