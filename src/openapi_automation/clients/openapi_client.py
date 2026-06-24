from __future__ import annotations

from typing import Any

from openapi_automation.core.file_loader import MultipartFiles
from openapi_automation.core.http_client import HttpClient


class ShanhaiOpenApiClient:
    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def create_api_key(self, *, user_id: str | int, admin_token: str | None = None):
        headers = {"X-Admin-Token": admin_token} if admin_token else None
        return self.http.post("/admin/api-key/create", json={"user_id": user_id}, headers=headers, auth="none")

    def clone_voice(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/voice/zeroshot/clone", files=_multipart_files(files, data), auth=auth)

    def infer_voice(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/voice/zeroshot/infer", files=_multipart_files(files, data), auth=auth)

    def generate_timbre(self, *, json: dict[str, Any], auth: str = "default"):
        return self.http.post(
            "/open/timbre-design/generate",
            json=json,
            auth=auth,
            headers={"Content-Type": "application/json"},
        )

    def translate(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/videots/translate", files=_multipart_files(files, data), auth=auth)

    def retranslate(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/videots/retranslate", files=_multipart_files(files, data), auth=auth)

    def back_translate(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/videots/back-translation", files=_multipart_files(files, data), auth=auth)

    def videots_status(self, *, params: dict[str, Any], auth: str = "default"):
        return self.http.get("/open/videots/status", params=params, auth=auth)

    def videots_download(self, *, params: dict[str, Any], auth: str = "default"):
        return self.http.get("/open/videots/download", params=params, auth=auth)

    def videots_tasks(self, *, auth: str = "default"):
        return self.http.get("/open/videots/tasks", auth=auth)

    def erase_subtitle(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/subtitle/erase", files=_multipart_files(files), params=data, auth=auth)

    def erase_result(self, *, params: dict[str, Any], auth: str = "default"):
        return self.http.get("/open/subtitle/erase/result", params=params, auth=auth)

    def asr_rest(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/asr", files=_multipart_files(files), params=data, auth=auth)

    def speaker_classify_submit(self, *, files: dict | None = None, auth: str = "default"):
        return self.http.post("/open/speaker-classify/submit", files=_multipart_files(files), auth=auth)

    def speaker_classify_status(self, *, params: dict[str, Any], auth: str = "default"):
        return self.http.get("/open/speaker-classify/status", params=params, auth=auth)

    def timbre_status(self, *, params: dict[str, Any], auth: str = "default"):
        return self.http.get("/open/timbre-design/status", params=params, auth=auth)

    def voice_separate(self, *, files: dict | None = None, data: dict | None = None, auth: str = "default"):
        return self.http.post("/open/voice/separate", files=_multipart_files(files, data), auth=auth)

    def voice_separate_status(self, *, params: dict[str, Any], auth: str = "default"):
        return self.http.get("/open/voice/separate/status", params=params, auth=auth)

    def video_compose(self, *, files: dict | None = None, params: dict | None = None, auth: str = "default"):
        return self.http.post("/open/video-compose/tasks", files=_multipart_files(files), params=params, auth=auth)

    def video_compose_status(self, *, params: dict[str, Any], auth: str = "default"):
        return self.http.get("/open/video-compose/status", params=params, auth=auth)


def build_files(test_data: dict, mapping: dict[str, str] | None = None) -> MultipartFiles:
    bundle = MultipartFiles()
    for field_name, file_key in (mapping or {}).items():
        bundle.add(field_name, test_data["files"][file_key])
    return bundle


def _multipart_files(files: dict | None = None, data: dict | None = None) -> dict:
    """Build a requests files payload that always forces multipart/form-data.

    requests falls back to application/x-www-form-urlencoded when only data= is
    supplied. Several backend upload endpoints reject that content type, even
    for missing-file negative cases, so form fields are represented as
    multipart fields via files=(None, value).
    """
    payload: dict = dict(files or {})
    for key, value in (data or {}).items():
        if value is not None:
            payload[key] = (None, str(value))
    if not payload:
        payload["__multipart_empty__"] = (None, "")
    return payload
