from __future__ import annotations

import time
from typing import Any

from config import ConnectorConfig
from exceptions import ConnectorError
from http_client import ensure_success, request_json


def request_membership_credential(config: ConnectorConfig, participant_api_key: str) -> dict[str, Any]:
    payload = {
        "issuerDid": config.trusted_issuer_did,
        "credentials": [
            {
                "format": "VC1_0_JWT",
                "type": "MembershipCredential",
                "id": config.membership_credential_definition_id,
            }
        ],
    }
    status, body = request_json(
        "POST",
        f"{config.wallet_identity_api}/v1alpha/participants/{config.participant_context_id}/credentials/request",
        payload,
        {"x-api-key": participant_api_key},
    )
    ensure_success(
        f"request membership credential for {config.participant_context_id}",
        status,
        body,
        allowed=(200, 201, 202, 204),
    )
    return {"status": status, "response": body}


def list_credentials(config: ConnectorConfig, participant_api_key: str) -> list[dict[str, Any]]:
    status, body = request_json(
        "GET",
        f"{config.wallet_identity_api}/v1alpha/participants/{config.participant_context_id}/credentials",
        headers={"x-api-key": participant_api_key},
    )
    ensure_success("list participant credentials", status, body, allowed=(200,))
    if not isinstance(body, list):
        raise ConnectorError(f"Credential endpoint returned no list: {body!r}")
    return [credential for credential in body if isinstance(credential, dict)]


def wait_for_membership_credential(
        config: ConnectorConfig,
        participant_api_key: str,
        attempts: int = 24,
        interval_seconds: float = 5,
) -> dict[str, Any]:
    for attempt in range(attempts):
        credentials = list_credentials(config, participant_api_key)
        credential = find_membership_credential(config, credentials)
        if credential is not None:
            return credential
        if attempt < attempts - 1:
            time.sleep(interval_seconds)
    raise ConnectorError(
        f"MembershipCredential from {config.trusted_issuer_did} did not arrive after {attempts} checks."
    )


def find_membership_credential(
        config: ConnectorConfig,
        credentials: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return next(
        (
            credential
            for credential in credentials
            if _is_membership_credential(
            credential,
            issuer_did=config.trusted_issuer_did,
            credential_definition_id=config.membership_credential_definition_id,
        )
        ),
        None,
    )


def _is_membership_credential(
        credential: dict[str, Any],
        issuer_did: str,
        credential_definition_id: str,
) -> bool:
    issuer = str(credential.get("issuerId") or credential.get("issuer") or "")
    metadata = credential.get("metadata")
    object_id = str(metadata.get("credentialObjectId") or "") if isinstance(metadata, dict) else ""
    serialized = str(credential)
    matches_type = object_id == credential_definition_id or "MembershipCredential" in serialized
    return (not issuer or issuer == issuer_did) and matches_type
