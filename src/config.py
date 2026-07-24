from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConnectorConfig(BaseSettings):
    """Runtime settings shared by connector lifecycle and data exchange operations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    connector_domain: str = ""
    connector_management_api: str = ""
    connector_management_api_key: str = "change-me"
    protocol: str = "dataspace-protocol-http:2025-1"

    participant_did: str = ""
    participant_context_id: str = ""
    participant_secret_alias: str = "participantsecret"
    participant_credential_service_url: str = ""
    participant_issuer_service_url: str = ""
    participant_dsp_callback_address: str = ""
    participant_dataplane_public_url: str = ""

    trusted_issuer_did: str = ""
    membership_credential_definition_id: str = "dev-credential-def-1"

    wallet_identity_api: str = "http://127.0.0.1:20100/api/identity"
    wallet_superuser_key: str = "YWRtaW4.change-me"

    vault_token: str = "change-me"
    vault_api: str = ""

    connector_stack_dir: Path = Path(".")
    state_path: Path = Field(
        default=Path(".state/participant.json"),
        validation_alias="CONNECTOR_ONBOARDING_STATE",
    )
    downloads_dir: Path = Path("downloads")

    @model_validator(mode="after")
    def validate_config(self):
        errors: list[str] = []

        # PARTICIPANT_DSP_CALLBACK_ADDRESS
        if not self.participant_dsp_callback_address:
            self.participant_dsp_callback_address = f"https://{self.connector_domain}/dsp"
        # PARTICIPANT_DATAPLANE_PUBLIC_URL
        if not self.participant_dataplane_public_url:
            self.participant_dataplane_public_url = f"https://{self.connector_domain}/public"
        # PARTICIPANT_CREDENTIAL_SERVICE_URL
        if not self.participant_credential_service_url:
            self.participant_credential_service_url = (
                f"https://{self.connector_domain}"
                f"/api/credentials/v1/participants/{self.participant_context_id}"
            )
        # PARTICIPANT_ISSUER_SERVICE_URL
        if not self.participant_issuer_service_url:
            self.participant_issuer_service_url = (
                f"https://{self.connector_domain}"
                f"/api/issuance/v1/participants/{self.participant_context_id}"
            )
        # CONNECTOR_MANAGEMENT_API
        if not self.connector_management_api:
            self.connector_management_api = (
                f"https://{self.connector_domain}/management"
            )
        # VAULT_API
        if not self.vault_api:
            self.vault_api = "http://127.0.0.1:28200"
        self.vault_api = self.vault_api.rstrip("/")

        # Checking missing values
        required = {
            "CONNECTOR_DOMAIN": self.connector_domain,
            "PARTICIPANT_DID": self.participant_did,
            "PARTICIPANT_CONTEXT_ID": self.participant_context_id,
            "TRUSTED_ISSUER_DID": self.trusted_issuer_did,
            "CONNECTOR_MANAGEMENT_API_KEY": self.connector_management_api_key,
        }

        missing = [
            name
            for name, value in required.items()
            if not value.strip()
        ]
        if missing:
            errors.append(f"[MISSING]: {', '.join(missing)}")

        # Checking default values
        placeholders = {
            "CONNECTOR_DOMAIN": self.connector_domain,
            "PARTICIPANT_DID": self.participant_did,
            "PARTICIPANT_CONTEXT_ID": self.participant_context_id,
            "TRUSTED_ISSUER_DID": self.trusted_issuer_did,
            "PARTICIPANT_CREDENTIAL_SERVICE_URL": self.participant_credential_service_url,
            "PARTICIPANT_ISSUER_SERVICE_URL": self.participant_issuer_service_url,
            "WALLET_SUPERUSER_KEY": self.wallet_superuser_key,
            "VAULT_TOKEN": self.vault_token,
            "CONNECTOR_MANAGEMENT_API_KEY": self.connector_management_api_key,
        }
        invalid = [
            name
            for name, value in placeholders.items()
            if "example.org" in value or "change-me" in value
        ]
        if not self.wallet_superuser_key.startswith("YWRtaW4."):
            invalid.append("WALLET_SUPERUSER_KEY (expected Identity Hub token prefix YWRtaW4.)")

        if invalid:
            errors.append(f"[INVALID]: {', '.join(invalid)}")

        if errors:
            raise ValueError("\n".join(errors))

        # print("Adjusting relative paths")
        stack_dir = self.connector_stack_dir
        if not stack_dir.is_absolute():
            stack_dir = (Path.cwd() / stack_dir).resolve()
            self.connector_stack_dir = stack_dir
            # print("Updating STACK_DIR to", self.stack_dir)

        state_path = self.state_path
        if not state_path.is_absolute():
            self.state_path = (stack_dir / self.state_path).resolve()
            # print("Updating STATE_PATH to", self.stack_dir)

        downloads_dir = self.downloads_dir
        if not downloads_dir.is_absolute():
            self.downloads_dir = (stack_dir / self.downloads_dir).resolve()
            # print("Updating DOWNLOADS_DIR to", self.stack_dir)
        return self

    @property
    def dsp_endpoint(self) -> str:
        base = self.participant_dsp_callback_address.rstrip("/")
        protocol_version = self.protocol.rsplit(":", 1)[-1]
        return base if base.endswith(f"/{protocol_version}") else f"{base}/{protocol_version}"

    @classmethod
    def from_env(
            cls,
            env_file: str | PathLike[str] | Sequence[str | PathLike[str]] | None = None,
            **overrides: object,
    ) -> Self:
        if env_file is None:
            return cls(**overrides)
        # noinspection PyArgumentList
        return cls(_env_file=env_file, **overrides)
