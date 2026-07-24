from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from exceptions import ConnectorError, ConnectorHttpError


def request_json(
    method: str,
    url: str,
    payload: Any = None,
    headers: dict[str, str] | None = None,
    timeout: int = 45,
) -> tuple[int, Any]:
    encoded = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = dict(headers or {})
    if payload is not None and not any(key.lower() == "content-type" for key in request_headers):
        request_headers["Content-Type"] = "application/json"
    req = request.Request(url, data=encoded, method=method.upper())
    for key, value in request_headers.items():
        req.add_header(key, value)

    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, _parse_body(response.read())
    except error.HTTPError as exc:
        return exc.code, _parse_body(exc.read())
    except error.URLError as exc:
        raise ConnectorError(f"HTTP request to {url} failed: {exc.reason}") from exc


def request_bytes(
    method: str,
    url: str,
    payload: bytes | str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 45,
) -> tuple[int, bytes, str]:
    encoded: bytes | None
    if isinstance(payload, str):
        encoded = payload.encode("utf-8")
    else:
        encoded = payload
    req = request.Request(url, data=encoded, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(), str(response.headers.get("content-type") or "")
    except error.HTTPError as exc:
        return exc.code, exc.read(), str(exc.headers.get("content-type") if exc.headers else "")
    except error.URLError as exc:
        raise ConnectorError(f"HTTP request to {url} failed: {exc.reason}") from exc


def ensure_success(
    operation: str,
    status: int,
    body: Any,
    allowed: tuple[int, ...] = (200, 201, 204),
) -> None:
    if status in allowed:
        return
    raise ConnectorHttpError(operation, status, body)


def require_field(body: Any, field: str, label: str) -> str:
    if not isinstance(body, dict) or not str(body.get(field, "")).strip():
        raise ConnectorError(f"Missing {field} in {label}: {json.dumps(body, indent=2, ensure_ascii=False)}")
    return str(body[field]).strip()


def _parse_body(body: bytes) -> Any:
    if not body:
        return None
    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
