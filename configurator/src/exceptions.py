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

from __future__ import annotations

import json
from typing import Any

class ConnectorError(RuntimeError):
    """Base exception raised by the connector client."""


class ConnectorHttpError(ConnectorError):
    """An HTTP operation against a connector component failed."""

    def __init__(self, operation: str, status: int, body: Any) -> None:
        details = body if isinstance(body, str) else json.dumps(body, indent=2, ensure_ascii=False)
        super().__init__(f"{operation} failed with HTTP {status}: {details}")
        self.operation = operation
        self.status = status
        self.body = body


class CatalogError(RuntimeError):
    pass
