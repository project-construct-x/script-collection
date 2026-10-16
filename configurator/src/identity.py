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

from typing import Any
from urllib import parse

from config import ConnectorConfig
from credentials import list_credentials
from exceptions import ConnectorError
from http_client import ensure_success, request_json, require_field

def create_or_reuse_participant(config: ConnectorConfig, state: dict[str, Any]) -> dict[str, str]:
    api_key = str(state.get("apiKey") or "").strip()
    client_secret = str(state.get("clientSecret") or "").strip()
    if api_key and client_secret:
        list_credentials(config, api_key)
        return {"apiKey": api_key, "clientSecret": client_secret}

    payload = {
        "scopes": [],
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
        f"{config.wallet_identity_api}/v1beta/participants",
        payload,
        {"x-api-key": config.wallet_superuser_key},
    )
    if status == 409:
        raise ConnectorError(
            f"Participant {config.participant_did} already exists in the wallet. "
            f"Restore the matching local state file at {config.state_path}."
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
