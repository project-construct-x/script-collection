from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import ConnectorConfig
from onboarding import initialize_participant, onboard_connector
from state import load_state
from tests.test_util import write_valid_config

def test_load_config_maps_identity_values_and_resolves_paths(tmp_path: Path) -> None:
    stack_dir = tmp_path / "connector"
    env_file = tmp_path / ".env"

    write_valid_config(env_file)

    config = ConnectorConfig.from_env(env_file, connector_stack_dir=stack_dir.resolve())

    assert config.connector_domain == "connector.test.local"
    assert config.participant_did == "did:web:connector.test.local:participant"
    assert config.participant_context_id == "participant"
    assert config.trusted_issuer_did == "did:web:issuer.test.local:issuer"
    assert config.wallet_identity_api == "http://127.0.0.1:20100/api/identity"
    assert config.wallet_superuser_key == "YWRtaW4.test-token"
    assert config.participant_credential_service_url == "https://connector.test.local/api/credentials/v1/participants/participant"
    assert config.participant_issuer_service_url == "https://connector.test.local/api/issuance/v1/participants/participant"
    assert config.participant_dsp_callback_address == "https://connector.test.local/dsp"
    assert config.dsp_endpoint == "https://connector.test.local/dsp/2025-1"
    assert config.participant_dataplane_public_url == "https://connector.test.local/public"
    assert config.state_path == (stack_dir / ".state" / "participant.json").resolve()
    assert config.downloads_dir == (stack_dir / "downloads").resolve()


def test_onboarding_rejects_example_configuration() -> None:
    with pytest.raises(ValueError, match="[INVALID]"):
        # use example config to not interfere with a present .env for local testing
        ConnectorConfig.from_env(".env.example")

def test_dsp_endpoint_does_not_duplicate_protocol_version(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    write_valid_config(env_file)
    config = ConnectorConfig.from_env(env_file, participant_dsp_callback_address="https://connector.test/dsp/2025-1")
    assert config.dsp_endpoint == "https://connector.test/dsp/2025-1"


# TODO fix test
# def test_client_lifecycle_uses_explicit_service_groups(monkeypatch, tmp_path: Path) -> None:
#     config = ConnectorConfig(connector_stack_dir=tmp_path, state_path=tmp_path / "state.json")
#     client = ConnectorClient(config)
#     compose_calls: list[tuple[Path, tuple[str, ...]]] = []
#
#     monkeypatch.setattr(
#         "client.start_services",
#         lambda compose_dir, services: compose_calls.append((Path(compose_dir), services)),
#     )
#     monkeypatch.setattr(
#         "onboarding.onboard_connector",
#         lambda selected_config, wait_for_credential=True: {
#             "participantDid": selected_config.participant_did,
#             "waited": wait_for_credential,
#         },
#     )
#
#     client.start_infrastructure()
#     result = client.request_membership_credential(wait_for_credential=False)
#
#     assert compose_calls == [
#         (tmp_path, INFRASTRUCTURE_SERVICES),
#         (tmp_path, CONNECTOR_SERVICES),
#     ]
#     assert result == {"participantDid": config.participant_did, "waited": False}


def test_initialize_participant_controls_only_local_components(monkeypatch, tmp_path: Path) -> None:
    state_path = tmp_path / ".state" / "participant.json"
    config = ConnectorConfig(
        connector_stack_dir=tmp_path,
        connector_domain="connector.test.local",
        participant_did="did:web:connector.test:participant",
        participant_context_id="participant",
        trusted_issuer_did="did:web:issuer.test:issuer",
        participant_credential_service_url="https://connector.test/api/credentials/participant",
        participant_issuer_service_url="https://connector.test/api/issuance/participant",
        wallet_superuser_key="YWRtaW4.test-key",
        vault_token="test-vault-token",
        connector_management_api_key="test-management-key",
        state_path=state_path,
    )
    vault_writes: list[str] = []

    monkeypatch.setattr(
        "onboarding.create_or_reuse_participant",
        lambda selected_config, state: {"apiKey": "participant-api-key", "clientSecret": "participant-secret"},
    )
    monkeypatch.setattr(
        "onboarding.write_participant_secret",
        lambda selected_config, secret: vault_writes.append(secret),
    )

    result = initialize_participant(config)
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert vault_writes == ["participant-secret"]
    assert result["participantDid"] == config.participant_did
    assert state == {
        "apiKey": "participant-api-key",
        "clientSecret": "participant-secret",
        "participantDid": config.participant_did,
        "participantContextId": "participant",
        "trustedIssuerDid": config.trusted_issuer_did,
        "credentialDefinitionId": "dev-credential-def-1",
    }


def test_onboard_requests_and_waits_for_membership_credential(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    write_valid_config(env_file)
    config = ConnectorConfig.from_env(env_file, connector_stack_dir=tmp_path, state_path=tmp_path / "state.json")
    calls: list[str] = []

    monkeypatch.setattr(
        "onboarding.initialize_participant",
        lambda selected_config: calls.append("bootstrap") or {"participantDid": selected_config.participant_did},
    )
    monkeypatch.setattr(
        "onboarding.load_state",
        lambda selected_config: {"apiKey": "participant-api-key"},
    )
    monkeypatch.setattr(
        "onboarding.list_credentials",
        lambda selected_config, key: [],
    )
    monkeypatch.setattr(
        "onboarding.request_membership_credential",
        lambda selected_config, key: calls.append(f"request:{key}") or {"status": 202, "response": None},
    )
    monkeypatch.setattr(
        "onboarding.wait_for_membership_credential",
        lambda selected_config, attempts=12: (
                calls.append("wait")
                or {
                    "issuerId": selected_config.trusted_issuer_did,
                    "state": "ISSUED",
                }
        ),
    )

    result = onboard_connector(config)

    assert calls == ["bootstrap", "request:participant-api-key", "wait"]
    assert result["credentialRequest"]["status"] == 202
    assert result["membershipCredential"]["state"] == "ISSUED"


def test_onboard_reuses_existing_membership_credential(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    write_valid_config(env_file)
    config = ConnectorConfig.from_env(env_file, connector_stack_dir=tmp_path, state_path=tmp_path / "state.json")
    existing = {
        "issuerId": config.trusted_issuer_did,
        "holderId": config.participant_did,
        "state": "ISSUED",
        "metadata": {"credentialObjectId": config.membership_credential_definition_id},
    }

    monkeypatch.setattr(
        "onboarding.initialize_participant",
        lambda selected_config: {"participantDid": selected_config.participant_did},
    )
    monkeypatch.setattr("onboarding.load_state", lambda selected_config: {"apiKey": "key"})
    monkeypatch.setattr(
        "onboarding.list_credentials",
        lambda selected_config, key: [existing],
    )
    monkeypatch.setattr(
        "onboarding.request_membership_credential",
        lambda selected_config, key: (_ for _ in ()).throw(AssertionError("must not request again")),
    )

    result = onboard_connector(config)

    assert result["credentialRequest"] == {"status": "skipped", "reason": "already-present"}
    assert result["membershipCredential"]["state"] == "ISSUED"


def test_load_state_normalizes_legacy_keys(tmp_path: Path) -> None:
    state_path = tmp_path / "participant.json"
    state_path.write_text(
        json.dumps(
            {
                "connectorApiKey": "api-key",
                "connectorSecret": "secret",
                "connectorDid": "did:web:connector.example.org:participant",
                "participantContextId": "participant",
            }
        ),
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    write_valid_config(env_file)
    config = ConnectorConfig.from_env(env_file, connector_stack_dir=tmp_path, state_path=state_path)

    state = load_state(config)

    assert state["apiKey"] == "api-key"
    assert state["clientSecret"] == "secret"
    assert state["participantDid"] == "did:web:connector.example.org:participant"
