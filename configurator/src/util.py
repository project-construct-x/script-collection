from typing import Any


def _read(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def dsp_endpoint_for_protocol(base_dsp: str, protocol: str) -> str:
    _, _, version = protocol.partition(":")
    if not version:
        return base_dsp

    base = base_dsp.rstrip("/")
    if base.endswith(f"/{version}"):
        return base

    return f"{base}/{version}"
