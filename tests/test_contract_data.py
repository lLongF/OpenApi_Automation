"""
测试数据契约校验（Contract Tests for Test Data）。

验证 data/test_data/*.yaml 中定义的测试用例数据完整性：
- 引用的 mock 文件是否存在
- 每个用例是否具备必填元数据（id/title/category/expected）
- 每个业务模块是否至少覆盖正向和反向用例
这些用例不依赖真实 API，无需 --live 参数。
"""

from __future__ import annotations

import pytest
from requests import Request

from openapi_automation.clients.openapi_client import _multipart_files
from openapi_automation.core.config import project_path


SMART_QUOTES = {
    "\u201c": 'Chinese left double quote: use "',
    "\u201d": 'Chinese right double quote: use "',
    "\u2018": "Chinese left single quote: use '",
    "\u2019": "Chinese right single quote: use '",
}


def _walk_cases(node):
    """递归遍历测试数据结构，提取符合用例格式的节点（包含 id/title/category/expected 字段）。"""
    if isinstance(node, dict):
        if {"id", "title", "category", "expected"}.issubset(node.keys()):
            yield node
        for value in node.values():
            yield from _walk_cases(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_cases(value)


@pytest.mark.contract
def test_all_mock_files_exist(test_data):
    """[契约测试] 验证 data/test_data/*.yaml 中 files 块引用的所有 mock 文件在磁盘上真实存在。"""
    for key, path in test_data["files"].items():
        assert project_path(path).exists(), f"Missing mock file for {key}: {path}"


@pytest.mark.contract
def test_case_definitions_have_required_metadata(test_data):
    """[契约测试] 验证所有测试用例均包含必填元数据：id（唯一）、title（非空）、category（合法枚举值）、expected。"""
    cases = list(_walk_cases(test_data))
    assert cases, "No cases were loaded from data/test_data/*.yaml"
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)), "Case ids must be unique"
    for case in cases:
        assert case["category"] in {"positive", "negative", "boundary", "exception"}
        assert case["title"].strip()


@pytest.mark.contract
def test_test_data_yaml_does_not_use_smart_quotes():
    """[契约测试] 验证 test_data.yaml 未误用中文弯引号，避免 YAML 字符串解析失败。"""
    paths = [project_path("data/test_data.yaml"), *sorted(project_path("data/test_data").glob("*.yaml"))]
    failures = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for quote, message in SMART_QUOTES.items():
                column = line.find(quote)
                if column != -1:
                    failures.append(f"{path}:{line_number}:{column + 1}: {message}: {line}")
    assert not failures, "\n".join(failures)


@pytest.mark.contract
def test_each_business_module_has_positive_and_negative_cases(test_data):
    """[契约测试] 验证每个业务模块（按 case id 前缀分组）至少包含 1 个正向用例和 1 个反向用例。"""
    cases = list(_walk_cases(test_data))
    by_prefix: dict[str, set[str]] = {}
    for case in cases:
        prefix = case["id"].split("_")[0]
        by_prefix.setdefault(prefix, set()).add(case["category"])
    for prefix, categories in by_prefix.items():
        assert "positive" in categories, f"{prefix} has no positive case"
        assert "negative" in categories, f"{prefix} has no negative case"


@pytest.mark.contract
def test_multipart_files_forces_multipart_when_file_is_missing():
    """[契约测试] 缺失文件的反向用例也必须以 multipart/form-data 发送，避免后端拒绝 x-www-form-urlencoded。"""
    request = Request("POST", "http://example.test", files=_multipart_files(data={"body": "{}"}))
    prepared = request.prepare()
    assert prepared.headers["Content-Type"].startswith("multipart/form-data")
