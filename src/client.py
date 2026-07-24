from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from catalog import Catalog, Offer
from config import ConnectorConfig
from credentials import list_credentials, request_membership_credential
from exceptions import ConnectorError
from onboarding import initialize_participant
from publish import publish_asset
from request import (
    negotiate_endpoint_reference,
    pull_data,
    request_asset,
    request_catalog,
    send_json_via_endpoint,
    wait_for_endpoint_data_reference, )
from state import load_state
from util import dsp_endpoint_for_protocol

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

@dataclass(slots=True)
class ConnectorClient:
    """High-level facade for one Construct-X connector."""

    config: ConnectorConfig

    def __init__(self, config: ConnectorConfig | None = None):
        if not config:
            config = ConnectorConfig()
        self.config = config

    def status(self):

        print("ConnectorClient version 0.1.0")
        print(f"Participant DID    : {self.config.participant_did}")
        print(f"Trusted Issuer DID : {self.config.trusted_issuer_did}")
        # print(f"EDC Host           : {self.config.connector_domain}")
        print(f"Connector DSP      : {self.config.participant_dsp_callback_address}")
        print(f"Management API     : {self.config.connector_management_api}")

        print("  Checking Management API... ", end="")
        try:
            self.check_management_api()
            print(f"{GREEN}OK{RESET}")
        except ConnectorError:
            print(f"{RED}FAILED{RESET}")
            # print(f"  Reason: {exc}")
            print("  Management API is unreachable or not authorized!")

        print("  Checking credentials... ", end="")
        try:
            self.check_configuration()
            print(f"{GREEN}OK{RESET}")
        except ConnectorError as e:
            print(f"{RED}FAILED{RESET}")
            print(f"  Reason: {e}")
            #print("Membership credentials could not be obtained! Check your configuration and EDC connection!")


    def bootstrap_participant(self) -> dict[str, str]:
        return initialize_participant(self.config)

    def request_membership_credential(self) -> dict[str, Any]:
        return request_membership_credential(self.config, self._participant_api_key())

    def list_credentials(self) -> list[dict[str, Any]]:
        return list_credentials(self.config, self._participant_api_key())

    def publish_http_asset(
            self,
            label: str,
            source_url: str,
            asset_id: str | None = None,
            content_type: str = "application/json",
            data_address_type: str = "HttpData",
            proxy_path: bool = False,
            proxy_method: bool = False,
            proxy_body: bool = False,
            proxy_query_params: bool = False,
    ) -> dict[str, Any]:
        return publish_asset(
            self.config,
            label=label,
            source_url=source_url,
            asset_id=asset_id,
            content_type=content_type,
            data_address_type=data_address_type,
            proxy_path=proxy_path,
            proxy_method=proxy_method,
            proxy_body=proxy_body,
            proxy_query_params=proxy_query_params,
        )

    def fetch_catalog(self, peer_did: str, peer_dsp: str, limit: int = 0) -> Catalog:
        return request_catalog(self.config, peer_did=peer_did, peer_dsp=peer_dsp, limit=limit)

    def request_http_asset(
            self,
            peer_did: str,
            peer_dsp: str,
            offer: Offer
    ) -> dict[str, str]:
        return request_asset(
            self.config,
            provider_did=peer_did,
            provider_dsp=peer_dsp,
            offer=offer,
        )

    # def negotiate_offer(
    #         self,
    #         peer_did: str,
    #         peer_dsp: str,
    #         offer: dict[str, Any],
    # ) -> dict[str, str]:
    #     negotiation_id = start_negotiation(
    #         self.config,
    #         provider_did=peer_did,
    #         provider_dsp=peer_dsp,
    #         asset_id=str(offer["assetId"]),
    #         offer_id=str(offer["offerId"]),
    #     )
    #     agreement_id = wait_for_agreement(self.config, negotiation_id)
    #     return {"negotiationId": negotiation_id, "agreementId": agreement_id}

    def negotiate_endpoint_reference(
            self,
            peer_did: str,
            peer_dsp: str,
            offer: Offer,
    ) -> dict[str, Any]:
        return negotiate_endpoint_reference(self.config, peer_did, peer_dsp, offer)

    def wait_for_endpoint_reference(self, transfer_id: str) -> dict[str, Any]:
        return wait_for_endpoint_data_reference(self.config, transfer_id)

    def download_asset(self, asset_id: str, endpoint_data: dict[str, Any]) -> str:
        return pull_data(self.config, asset_id, endpoint_data)

    def send_json_via_endpoint(
            self,
            endpoint_data: dict[str, Any],
            payload: Any,
            method: str = "POST",
            path: str = "",
            query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return send_json_via_endpoint(endpoint_data, payload, method=method, path=path, query=query)

    def _participant_api_key(self) -> str:
        state = load_state(self.config)
        api_key = str(state.get("apiKey") or "")
        if not api_key:
            raise FileNotFoundError(f"Participant state does not contain an API key: {self.config.state_path}")
        return api_key

    def check_configuration(self) -> bool:
        try:
            credentials = self.list_credentials()
            if not credentials:
                raise ConnectorError("No valid credentials found. Check your configuration!")
        except Exception:
            raise ConnectorError("Error connecting to wallet service. Check your configuration!") from None
        return True

    def check_management_api(self) -> bool:
        """Verify the connector through a catalog request to its own DSP endpoint."""
        catalog = self.fetch_catalog(peer_did=self.config.participant_did,
                                     peer_dsp=dsp_endpoint_for_protocol(
                                         base_dsp=self.config.participant_dsp_callback_address,
                                         protocol=self.config.protocol), limit=1)
        if catalog:
            return True
        else:
            return False
