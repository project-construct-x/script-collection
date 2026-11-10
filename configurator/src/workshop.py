# Copyright (c) 2026 Bergische Universitaet Wuppertal
# SPDX-License-Identifier: Apache-2.0

"""Local configuration for the isolated workshop deployment."""

import json
import re
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key


def prepare_environment(path: Path = Path(".env")) -> None:
    values = dotenv_values(path)
    domain = values.get("CONNECTOR_DOMAIN", "")
    if not re.fullmatch(r"teilnehmer(0[1-9]|10)\.dataspace-portal\.com", domain):
        raise ValueError("CONNECTOR_DOMAIN must be teilnehmer01 through teilnehmer10.dataspace-portal.com")
    token = values.get("CLOUDFLARE_TUNNEL_TOKEN", "")
    if not token or token.startswith("change-me"):
        raise ValueError("Set the individual CLOUDFLARE_TUNNEL_TOKEN in .env")
    expected_did = f"did:web:{domain}:participant"
    state_path = Path(values.get("CONNECTOR_ONBOARDING_STATE") or ".state/participant.json")
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("participantDid") != expected_did:
            raise ValueError("This directory already contains another participant's identity. Use a fresh copy.")
    updates = {"PARTICIPANT_DID": expected_did}
    for name in ("CONNECTOR_MANAGEMENT_API_KEY", "POSTGRES_PASSWORD", "VAULT_TOKEN", "WALLET_SUPERUSER_KEY"):
        if not values.get(name) or "change-me" in values[name]:
            updates[name] = ("YWRtaW4." if name == "WALLET_SUPERUSER_KEY" else "") + secrets.token_urlsafe(24)
    for name, value in updates.items():
        set_key(path, name, value)
    path.chmod(0o600)
