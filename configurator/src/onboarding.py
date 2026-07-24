from __future__ import annotations

from typing import Any

from config import ConnectorConfig
from credentials import (
    find_membership_credential,
    list_credentials,
    request_membership_credential
)
from identity import create_or_reuse_participant, write_participant_secret, wait_for_membership_credential
from state import load_state, remember_public_values, save_state


def initialize_participant(config: ConnectorConfig) -> dict[str, str]:
    """Create the participant locally and store its client secret in Vault."""

    state = load_state(config)
    participant = create_or_reuse_participant(config, state)
    state.update(participant)
    remember_public_values(config, state)

    # Persist first: Identity Hub only returns the generated secret once. If
    # Vault is temporarily unavailable, the next run can safely retry the copy.
    save_state(config, state)
    write_participant_secret(config, participant["clientSecret"])

    return {
        "trustedIssuerDid": config.trusted_issuer_did,
        "participantDid": config.participant_did,
        "stateFile": str(config.state_path),
    }


def onboard_connector(config: ConnectorConfig, wait_for_credential: bool = True) -> dict[str, Any]:
    """Bootstrap the local participant and request its membership credential."""

    result: dict[str, Any] = initialize_participant(config)
    participant_api_key = str(load_state(config)["apiKey"])
    credential = find_membership_credential(config, list_credentials(config, participant_api_key))
    if credential is None:
        result["credentialRequest"] = request_membership_credential(config, participant_api_key)
        if wait_for_credential:
            credential = wait_for_membership_credential(config)
    else:
        result["credentialRequest"] = {"status": "skipped", "reason": "already-present"}

    if credential is not None:
        result["membershipCredential"] = {
            "issuerId": credential.get("issuerId"),
            "holderId": credential.get("holderId"),
            "state": credential.get("state"),
        }
    return result
