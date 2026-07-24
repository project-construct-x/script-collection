from __future__ import annotations

import json
from typing import Any

from config import ConnectorConfig


def load_state(config: ConnectorConfig) -> dict[str, Any]:
    """Load state and normalize keys written by older Python and shell flows."""

    if not config.state_path.exists():
        return {}
    state = json.loads(config.state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError(f"Participant state must be a JSON object: {config.state_path}")

    aliases = {
        "apiKey": ("connectorApiKey",),
        "clientSecret": ("connectorSecret",),
        "participantDid": ("connectorDid", "did"),
        "participantContextId": ("connectorContext",),
    }
    for canonical, legacy_keys in aliases.items():
        if state.get(canonical):
            continue
        for legacy_key in legacy_keys:
            if state.get(legacy_key):
                state[canonical] = state[legacy_key]
                break
    return state


def save_state(config: ConnectorConfig, state: dict[str, Any]) -> None:
    config.state_path.parent.mkdir(parents=True, exist_ok=True)
    config.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    config.state_path.chmod(0o660)


def remember_public_values(config: ConnectorConfig, state: dict[str, Any]) -> None:
    state.update(
        {
            "participantDid": config.participant_did,
            "participantContextId": config.participant_context_id,
            "trustedIssuerDid": config.trusted_issuer_did,
            "credentialDefinitionId": config.membership_credential_definition_id,
        }
    )
    for legacy_key in ("connectorApiKey", "connectorSecret", "connectorDid", "did"):
        state.pop(legacy_key, None)
