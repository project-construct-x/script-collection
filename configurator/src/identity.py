from __future__ import annotations

import json
import time
from typing import Any
from urllib import parse

from config import ConnectorConfig
from http_client import ensure_success, request_json, require_field


def local_credentials(config) -> list[dict[str, Any]]:
    state = json.loads(config.state_path.read_text())
    url = f"{config.wallet_identity_api}/v1alpha/participants/{config.participant_context_id}/credentials"
    status, body = request_json("GET", url, headers={"x-api-key": state["apiKey"]})  # this should be private!
    if status != 200:
        raise RuntimeError(f"Wallet credential query failed with HTTP {status}: {body}")
    return body if isinstance(body, list) else []


def wait_for_membership_credential(config, attempts: int = 12) -> list[dict[str, Any]]:
    for _ in range(attempts):
        credentials = local_credentials(config)
        if credentials:
            return credentials
        time.sleep(5)
    raise RuntimeError("Membership Credential Could not be retrieved!")


def create_or_reuse_participant(config: ConnectorConfig, state: dict[str, Any]) -> dict[str, str]:
    api_key = str(state.get("apiKey") or "").strip()
    client_secret = str(state.get("clientSecret") or "").strip()
    if api_key and client_secret:
        try:
            # Test access the identity service using obtained secrets
            local_credentials(config)
            return {"apiKey": api_key, "clientSecret": client_secret}
        except RuntimeError:
            print("Could not access wallet resources. Re-initializing...")

    # We found no api key or could not access the resources it refers to. Re-initialize wallet identity.
    payload = {
        "roles": [],
        "serviceEndpoints": [
            {
                "id": f"{config.participant_context_id}-CredentialService",
                "type": "CredentialService",
                "serviceEndpoint": config.participant_credential_service_url,
            },
            {
                "id": f"{config.participant_context_id}-IssuerService",
                "type": "IssuerService",
                "serviceEndpoint": config.participant_issuer_service_url,
            },
        ],
        "active": True,
        "participantContextId": config.participant_context_id,
        "did": config.participant_did,
        "key": {
            "keyId": f"{config.participant_did}#key-1",
            "privateKeyAlias": f"{config.participant_did}-alias",
            "keyGeneratorParams": {"algorithm": "EdDSA", "curve": "Ed25519"},
        },
    }
    status, body = request_json(
        "POST",
        f"{config.wallet_identity_api}/v1alpha/participants",
        payload,
        {"x-api-key": config.wallet_superuser_key},
    )
    ensure_success(f"create participant {config.participant_did}", status, body, allowed=(200, 201))
    return {
        "apiKey": require_field(body, "apiKey", "participant response"),
        "clientSecret": require_field(body, "clientSecret", "participant response"),
    }


def write_participant_secret(config: ConnectorConfig, client_secret: str) -> None:
    status, body = request_json(
        "POST",
        f"{config.vault_api}/v1/secret/data/{parse.quote(config.participant_secret_alias, safe='')}",
        {"data": {"content": client_secret}},
        {"X-Vault-Token": config.vault_token},
    )
    ensure_success(
        f"write Vault secret {config.participant_secret_alias} at {config.vault_api}",
        status,
        body,
    )
