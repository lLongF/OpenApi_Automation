from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import EnvConfig


class HttpClient:
    def __init__(self, config: EnvConfig, api_key: str | None = None) -> None:
        self.config = config
        self.api_key = api_key
        self.session = requests.Session()
        retry = Retry(
            total=config.retry.total,
            read=config.retry.total,
            connect=config.retry.total,
            backoff_factor=config.retry.backoff_factor,
            status_forcelist=config.retry.status_forcelist,
            allowed_methods=frozenset({"GET", "POST"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def request(
        self,
        method: str,
        path: str,
        *,
        auth: str = "default",
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        request_headers = dict(headers or {})
        if auth == "default":
            if self.api_key:
                request_headers["api_key"] = self.api_key
        elif auth == "invalid":
            request_headers["api_key"] = "invalid-api-key-for-negative-test"
        elif auth == "none":
            pass
        else:
            request_headers["api_key"] = auth

        timeout = kwargs.pop("timeout", self.config.timeout.requests_tuple)
        url = path if path.startswith(("http://", "https://")) else f"{self.config.base_url}{path}"
        return self.session.request(method, url, headers=request_headers, timeout=timeout, **kwargs)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)
