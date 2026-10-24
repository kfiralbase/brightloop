"""Minimal Base44 REST client: upload a public file, upsert entity records.

Standard library only. The Entities and file APIs are in beta, so every call to them lives here.
Docs: https://docs.base44.com/api-reference/upsert-entity-records
      https://docs.base44.com/api-reference/upload-app-file
"""

from __future__ import annotations

import json
import mimetypes
import os
import uuid
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError

API = "https://app.base44.com"
UPSERT_BATCH = 500  # the API's per-call maximum


class Base44Error(RuntimeError):
    pass


class Base44Store:
    def __init__(self, app_id: str, token: str, *, api: str = API, opener=request.urlopen, timeout: int = 60):
        self.app_id, self._token, self.api = app_id, token, api.rstrip("/")
        self._open, self._timeout = opener, timeout

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Base44Store | None":
        env = os.environ if env is None else env
        app_id, token = env.get("BASE44_APP_ID", "").strip(), env.get("BASE44_TOKEN", "").strip()
        return cls(app_id, token) if app_id and token else None

    def _call(self, method: str, path: str, body: bytes, content_type: str) -> object:
        req = request.Request(self.api + path, data=body, method=method, headers={
            "Authorization": f"Bearer {self._token}", "Content-Type": content_type, "Accept": "application/json"})
        try:
            with self._open(req, timeout=self._timeout) as resp:
                raw = resp.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise Base44Error(f"{method} {path} → HTTP {exc.code}: {detail}") from None
        except URLError as exc:
            raise Base44Error(f"{method} {path} → {exc.reason}") from None
        return json.loads(raw) if raw else None

    def upload(self, path: Path) -> str:
        """Upload a file as public and return its permanent URL."""
        boundary = uuid.uuid4().hex
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = b"".join([
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"visibility\"\r\n\r\npublic\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n".encode(),
            path.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        out = self._call("POST", f"/api/files/apps/{self.app_id}/upload", body,
                         f"multipart/form-data; boundary={boundary}")
        url = out.get("url") if isinstance(out, dict) else None
        if not url:
            raise Base44Error(f"upload of {path.name} returned no url")
        return url

    def upsert(self, entity: str, key: str | list[str], records: list[dict]) -> int:
        """Create or update records matched on key. Returns how many were written."""
        written = 0
        for start in range(0, len(records), UPSERT_BATCH):
            batch = records[start:start + UPSERT_BATCH]
            body = json.dumps({"key": key, "records": batch}).encode()
            self._call("POST", f"/api/apps/{self.app_id}/entities/{entity}/upsert", body, "application/json")
            written += len(batch)
        return written
