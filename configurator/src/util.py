# Copyright (c) 2026 Bergische Universität Wuppertal
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
#
# Contributors:
#   TMDT der Bergischen Universität Wuppertal

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
