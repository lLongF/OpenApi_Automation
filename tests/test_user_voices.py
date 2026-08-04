"""当前用户个人音色接口测试。

覆盖接口：
- POST   /open/voice/zeroshot/save
- GET    /open/voice/user-voices/page
- PUT    /open/voice/user-voices
- DELETE /open/voice/user-voices

正向写操作使用独立的克隆 request_id 和随机音色名；fixture 会在测试结束时尽力清理
尚未删除的个人音色，因此该模块既可单独运行，也可在完整套件中运行。
"""

from __future__ import annotations

import uuid
import warnings
from typing import Any

import pytest

from openapi_automation.core.assertions import response_json

from .helpers import assert_case, case_ids, case_params, rendered
from .test_voice import clone_voice_and_get_speaker_id


SUCCESS_CODES = {0, 200}
PERSONAL_VOICE_FIELDS = (
    "voice_name",
    "description",
    "lang_code",
    "gender_value",
    "age_value",
    "timbre_value",
    "audio_url",
    "create_time",
    "update_time",
)


def pytest_generate_tests(metafunc):
    """根据个人音色四个接口的 YAML 模块动态生成参数化用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()
    mapping = {
        "save_case": data["user_voice_save"]["cases"],
        "page_case": data["user_voice_page"]["cases"],
        "update_case": data["user_voice_update"]["cases"],
        "delete_case": data["user_voice_delete"]["cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.fixture
def user_voice_factory(api_client, test_data):
    """为每个测试创建独立的个人音色工厂，并在结束后清理残留数据。"""
    factory = _UserVoiceFactory(api_client, test_data)
    try:
        yield factory
    finally:
        factory.cleanup()


@pytest.mark.live
def test_save_cloned_voice(api_client, common, save_case, user_voice_factory):
    """[Live 测试] 保存克隆音色，并用分页接口按新名称验证保存结果。"""
    case = rendered(save_case, common)
    body = dict(case.get("json") or {})
    if case.get("use_existing_voice_name"):
        existing_voice = user_voice_factory.create("save-duplicate")
        body["voice_name"] = existing_voice["name"]
    if case.get("use_clone_request_id"):
        body["request_id"] = user_voice_factory.clone_request_id()
    if case.get("use_unique_voice_name"):
        body["voice_name"] = _new_name("save")

    response = api_client.save_cloned_voice(json=body, auth=case.get("auth", "default"))
    payload = assert_case(response, case)

    if case.get("auth") in {"none", "invalid"}:
        assert not _is_success(payload), payload
    elif _is_success(payload):
        name = body.get("voice_name")
        assert isinstance(name, str) and name, payload
        user_voice_factory.track(name)
        page_payload = user_voice_factory.page(voice_name=name)
        item = _find_exact_voice(page_payload, name)
        assert item is not None, f"保存成功后未能按 voice_name 查询到个人音色: {name!r}; 响应: {page_payload!r}"
        _assert_personal_voice_item(item)


@pytest.mark.live
def test_user_voices_page(api_client, common, page_case, user_voice_factory):
    """[Live 测试] 分页查询当前用户的个人音色。"""
    case = rendered(page_case, common)
    params = dict(case.get("params") or {})
    expected_name: str | None = None
    expected_fields: dict[str, Any] | None = None

    if case.get("create_voice"):
        voice = user_voice_factory.create("page")
        expected_name = voice["name"]
        params["voice_name"] = expected_name
        if case.get("use_all_filters"):
            expected_fields = voice["attributes"]
            params.update(expected_fields)
    elif case.get("use_absent_voice_name"):
        params["voice_name"] = _new_name("absent")

    response = api_client.user_voices_page(params=params, auth=case.get("auth", "default"))
    payload = assert_case(response, case)

    if case.get("auth") in {"none", "invalid"}:
        assert not _is_success(payload), payload
    elif _is_success(payload):
        _assert_personal_voice_page(
            payload,
            params,
            expected_name=expected_name,
            expected_fields=expected_fields,
            expect_empty_result=bool(case.get("expect_empty_result")),
        )


@pytest.mark.live
def test_update_user_voice(api_client, common, update_case, user_voice_factory):
    """[Live 测试] 按旧名称更新个人音色，并验证名称或属性已持久化。"""
    case = rendered(update_case, common)
    workflow = case.get("workflow")

    if workflow:
        _run_update_workflow(api_client, case, user_voice_factory)
        return

    body = dict(case.get("json") or {})
    name = case.get("name")
    if case.get("create_voice"):
        voice = user_voice_factory.create("update-negative")
        name = voice["name"]

    response = api_client.update_user_voice(name=name, json=body, auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("auth") in {"none", "invalid"}:
        assert not _is_success(payload), payload


@pytest.mark.live
def test_delete_user_voice(api_client, common, delete_case, user_voice_factory):
    """[Live 测试] 按名称软删除个人音色，并确认分页查询不可见。"""
    case = rendered(delete_case, common)
    if case.get("workflow") == "delete_and_verify_absent":
        voice = user_voice_factory.create("delete")
        name = voice["name"]
        response = api_client.delete_user_voice(name=name, auth=case.get("auth", "default"))
        payload = assert_case(response, case)
        assert _is_success(payload), payload
        user_voice_factory.forget(name)

        page_payload = user_voice_factory.page(voice_name=name)
        data = _page_data(page_payload)
        assert data["list"] == [], f"软删除后仍可按名称查询到个人音色 {name!r}: {page_payload!r}"
        assert data["total"] == 0, page_payload
        return

    name = case.get("name")
    if case.get("create_voice"):
        voice = user_voice_factory.create("delete-negative")
        name = voice["name"]

    response = api_client.delete_user_voice(name=name, auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("auth") in {"none", "invalid"}:
        assert not _is_success(payload), payload


class _UserVoiceFactory:
    """创建、查询并跟踪测试期间产生的个人音色。"""

    _DEFAULT_ATTRIBUTES = {
        "lang_code": "zh",
        "gender_value": "1",
        "age_value": "1",
        "timbre_value": "1",
    }

    def __init__(self, api_client, test_data: dict[str, Any]) -> None:
        self.api_client = api_client
        self.test_data = test_data
        self._tracked_names: set[str] = set()

    def clone_request_id(self) -> str:
        return clone_voice_and_get_speaker_id(self.api_client, self.test_data)

    def create(self, prefix: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """克隆并保存一个新个人音色，再用分页接口确认已保存。"""
        name = _new_name(prefix)
        body = {
            "request_id": self.clone_request_id(),
            "voice_name": name,
            **self._DEFAULT_ATTRIBUTES,
            "text": "个人音色接口自动化测试文本",
            "description": "自动化测试创建的个人音色",
        }
        body.update(overrides or {})
        name = str(body["voice_name"])
        response = self.api_client.save_cloned_voice(json=body)
        payload = _assert_success_response(response, "保存克隆音色")
        self.track(name)

        page_payload = self.page(voice_name=name)
        item = _find_exact_voice(page_payload, name)
        assert item is not None, f"保存后未能按名称查询个人音色 {name!r}: {page_payload!r}"
        _assert_personal_voice_item(item)
        attributes = {field: body[field] for field in self._DEFAULT_ATTRIBUTES}
        return {"name": name, "attributes": attributes, "payload": payload}

    def page(self, **params: Any) -> dict[str, Any]:
        query = {"page_no": 1, "page_size": 20, **params}
        response = self.api_client.user_voices_page(params=query)
        payload = _assert_success_response(response, "分页查询个人音色")
        _assert_personal_voice_page(payload, query)
        return payload

    def track(self, name: str) -> None:
        self._tracked_names.add(name)

    def rename(self, old_name: str, new_name: str) -> None:
        self._tracked_names.discard(old_name)
        self._tracked_names.add(new_name)

    def forget(self, name: str) -> None:
        self._tracked_names.discard(name)

    def cleanup(self) -> None:
        """清理本测试创建但未在工作流内删除的音色，不覆盖原测试失败。"""
        for name in tuple(self._tracked_names):
            try:
                response = self.api_client.delete_user_voice(name=name)
                payload = response_json(response)
                if response.status_code != 200 or not _is_success(payload):
                    warnings.warn(
                        f"个人音色测试清理失败，name={name!r}，response={payload!r}",
                        stacklevel=2,
                    )
            except Exception as exc:  # pragma: no cover - cleanup must not mask the test result
                warnings.warn(f"个人音色测试清理异常，name={name!r}，error={exc!r}", stacklevel=2)
            finally:
                self._tracked_names.discard(name)


def _run_update_workflow(api_client, case: dict[str, Any], factory: _UserVoiceFactory) -> None:
    voice = factory.create("update")
    old_name = voice["name"]
    body = dict(case.get("json") or {})
    workflow = case["workflow"]

    if workflow == "rename_and_edit":
        new_name = _new_name("updated")
        body["voice_name"] = new_name
    elif workflow == "description_only":
        new_name = old_name
    elif workflow == "duplicate_voice_name":
        duplicate_voice = factory.create("update-duplicate")
        new_name = duplicate_voice["name"]
        body["voice_name"] = new_name
    else:  # pragma: no cover - YAML workflow validation
        raise AssertionError(f"Unsupported user voice update workflow: {workflow!r}")

    before_payload = factory.page(voice_name=old_name)
    before_item = _find_exact_voice(before_payload, old_name)
    assert before_item is not None, f"更新前未查询到个人音色 {old_name!r}: {before_payload!r}"

    response = api_client.update_user_voice(name=old_name, json=body, auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if workflow == "duplicate_voice_name":
        assert not _is_success(payload), payload
        after_payload = factory.page(voice_name=old_name)
        assert _find_exact_voice(after_payload, old_name) is not None, (
            f"重名更新失败后原个人音色不应被修改: {after_payload!r}"
        )
        return
    assert _is_success(payload), payload

    if new_name != old_name:
        factory.rename(old_name, new_name)
        after_payload = factory.page(voice_name=new_name)
        after_item = _find_exact_voice(after_payload, new_name)
        assert after_item is not None, f"更新后未查询到新名称 {new_name!r}: {after_payload!r}"
        assert after_item["voice_name"] != before_item["voice_name"], (before_item, after_item)

        old_name_payload = factory.page(voice_name=old_name)
        assert _find_exact_voice(old_name_payload, old_name) is None, (
            f"更新名称后旧名称仍可查询到: {old_name_payload!r}"
        )
    else:
        after_payload = factory.page(voice_name=old_name)
        after_item = _find_exact_voice(after_payload, old_name)
        assert after_item is not None, after_payload

    for field, expected_value in body.items():
        if field == "voice_name":
            continue
        assert str(after_item.get(field)) == str(expected_value), (field, expected_value, after_item)


def _assert_success_response(response, operation: str) -> dict[str, Any]:
    payload = response_json(response)
    assert response.status_code == 200, f"{operation} HTTP 状态异常: {response.status_code}, {payload!r}"
    assert _is_success(payload), f"{operation} 业务响应异常: {payload!r}"
    return payload


def _is_success(payload: dict[str, Any] | None) -> bool:
    return bool(isinstance(payload, dict) and payload.get("code") in SUCCESS_CODES)


def _page_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    assert isinstance(data, dict), payload
    assert isinstance(data.get("list"), list), payload
    assert isinstance(data.get("total"), int) and data["total"] >= 0, payload
    return data


def _assert_personal_voice_page(
    payload: dict[str, Any],
    params: dict[str, Any],
    *,
    expected_name: str | None = None,
    expected_fields: dict[str, Any] | None = None,
    expect_empty_result: bool = False,
) -> None:
    data = _page_data(payload)
    items = data["list"]
    page_size = params.get("page_size")
    if isinstance(page_size, int) and page_size > 0:
        assert len(items) <= page_size, payload
    for item in items:
        _assert_personal_voice_item(item)

    if expect_empty_result:
        assert items == [], payload
        assert data["total"] == 0, payload
    if expected_name is not None:
        item = _find_exact_voice(payload, expected_name)
        assert item is not None, f"未查询到名称为 {expected_name!r} 的个人音色: {payload!r}"
        for field, expected_value in (expected_fields or {}).items():
            assert str(item.get(field)) == str(expected_value), (field, expected_value, item)


def _assert_personal_voice_item(item: Any) -> None:
    assert isinstance(item, dict), item
    for field in PERSONAL_VOICE_FIELDS:
        assert field in item, item
    assert isinstance(item["voice_name"], str) and item["voice_name"].strip(), item
    assert item["description"] is None or isinstance(item["description"], str), item
    assert item["lang_code"] is None or isinstance(item["lang_code"], str), item
    assert isinstance(item["audio_url"], str) and item["audio_url"].strip(), item


def _find_exact_voice(payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in _page_data(payload)["list"]:
        if isinstance(item, dict) and item.get("voice_name") == name:
            return item
    return None


def _new_name(prefix: str) -> str:
    return f"测试个人音色-{prefix}-{uuid.uuid4().hex[:12]}"
