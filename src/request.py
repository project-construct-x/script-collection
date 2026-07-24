from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib import parse

from catalog import Catalog, Offer
from config import ConnectorConfig
from exceptions import ConnectorError
from http_client import ensure_success, request_bytes, request_json
from payloads import (
    catalog_request_payload,
    contract_request_payload,
    http_data_destination,
    transfer_request_payload,
)
from util import _read

LOGGER = logging.getLogger(__name__)


def request_catalog(config: ConnectorConfig, peer_did: str, peer_dsp: str, limit: int = 0) -> Catalog:
    """Request a provider's DSP catalog and return it as a Catalog object.

    Args:
        config: Connector configuration, including the management API base URL.
        peer_did: DID of the provider connector to request the catalog from.
        peer_dsp: DSP endpoint URL of the provider connector.
        limit: Limit the amount of offers requested. 0 is unlimited.

    Returns:
        The parsed Catalog, containing zero or more Offer objects.

    Raises:
        ConnectorError: If the catalog request does not return a 200 status.
    """
    status, body = request_json(
        "POST",
        f"{config.connector_management_api}/v3/catalog/request",
        catalog_request_payload(peer_dsp, config.protocol, peer_did, limit),
        _management_headers(config),
    )
    ensure_success("request catalog", status, body, allowed=(200,))
    return Catalog.from_dict(body if isinstance(body, dict) else {})


def select_offer(catalog: list[dict[str, Any]], asset_id: str = "") -> dict[str, Any]:
    if asset_id:
        for offer in catalog:
            if offer.get("assetId") == asset_id:
                return offer
        raise ConnectorError(f"No offer found for asset id: {asset_id}")
    if not catalog:
        raise ConnectorError("Provider catalog is empty.")
    return catalog[0]


def start_negotiation(
        config: ConnectorConfig,
        provider_did: str,
        provider_dsp: str,
        asset_id: str,
        offer_id: str,
) -> str:
    status, body = request_json(
        "POST",
        f"{config.connector_management_api}/v3/contractnegotiations",
        contract_request_payload(
            peer_did=provider_did,
            peer_dsp=provider_dsp,
            consumer_did=config.participant_did,
            protocol=config.protocol,
            asset_id=asset_id,
            offer_id=offer_id,
        ),
        {**_management_headers(config), "Accept": "application/json"},
    )
    ensure_success("start negotiation", status, body, allowed=(200, 201, 202))
    negotiation_id = _id_from_response(body)
    if not negotiation_id:
        raise ConnectorError(f"Negotiation id missing: {body}")
    return negotiation_id


def wait_for_agreement(
        config: ConnectorConfig,
        negotiation_id: str,
        attempts: int = 45,
        interval_seconds: float = 2,
) -> str:
    for attempt in range(1, attempts + 1):
        status, body = request_json(
            "GET",
            f"{config.connector_management_api}/v3/contractnegotiations/{parse.quote(negotiation_id, safe='')}",
            headers={**_management_headers(config), "Accept": "application/json"},
        )
        ensure_success(f"negotiation poll {attempt}", status, body, allowed=(200,))
        state = str(_read(body, "edc:state", "state") or "").lower() if isinstance(body, dict) else ""
        LOGGER.debug("Negotiation poll %s: %s", attempt, state or "<unknown>")
        if state == "finalized":
            agreement_id = str(_read(body, "edc:contractAgreementId", "contractAgreementId") or "")
            if agreement_id:
                return agreement_id
        if state in {"terminated", "error"}:
            raise ConnectorError(f"Negotiation ended with {state}: {body}")
        if attempt < attempts:
            time.sleep(interval_seconds)
    raise ConnectorError("Negotiation did not finalize in time.")


def start_pull_transfer(
        config: ConnectorConfig,
        peer_did: str,
        peer_dsp: str,
        agreement_id: str,
) -> str:
    status, body = request_json(
        "POST",
        f"{config.connector_management_api}/v3/transferprocesses",
        transfer_request_payload(
            peer_did=peer_did,
            peer_dsp=peer_dsp,
            protocol=config.protocol,
            agreement_id=agreement_id,
            transfer_type="HttpData-PULL",
        ),
        _management_headers(config),
    )
    ensure_success("start transfer", status, body, allowed=(200, 201, 202))
    transfer_id = _id_from_response(body)
    if not transfer_id:
        raise ConnectorError(f"Transfer id missing: {body}")
    return transfer_id


def start_push_transfer(
        config: ConnectorConfig,
        peer_did: str,
        peer_dsp: str,
        agreement_id: str,
        sink_base_url: str,
        sink_path: str = "",
        sink_method: str = "POST",
        sink_content_type: str = "application/json",
) -> str:
    status, body = request_json(
        "POST",
        f"{config.connector_management_api}/v3/transferprocesses",
        transfer_request_payload(
            peer_did=peer_did,
            peer_dsp=peer_dsp,
            protocol=config.protocol,
            agreement_id=agreement_id,
            transfer_type="HttpData-PUSH",
            data_destination=http_data_destination(
                base_url=sink_base_url,
                path=sink_path,
                method=sink_method,
                content_type=sink_content_type,
            ),
        ),
        _management_headers(config),
    )
    ensure_success("start push transfer", status, body, allowed=(200, 201, 202))
    transfer_id = _id_from_response(body)
    if not transfer_id:
        raise ConnectorError(f"Transfer id missing: {body}")
    return transfer_id


def wait_for_endpoint_data_reference(
        config: ConnectorConfig,
        transfer_id: str,
        attempts: int = 45,
        interval_seconds: float = 2,
) -> dict[str, Any]:
    for attempt in range(1, attempts + 1):
        status, body = request_json(
            "GET",
            f"{config.connector_management_api}/v3/edrs/{parse.quote(transfer_id, safe='')}/dataaddress",
            headers={**_management_headers(config), "Accept": "application/json"},
        )
        if status in {404, 409}:
            LOGGER.debug("Endpoint reference poll %s: not ready (%s)", attempt, status)
        elif status >= 400:
            ensure_success("request endpoint data reference", status, body, allowed=(200,))
        if isinstance(body, dict) and body.get("authorization"):
            LOGGER.debug("Endpoint reference poll %s: ready", attempt)
            return body
        LOGGER.debug("Endpoint reference poll %s: incomplete", attempt)
        if attempt < attempts:
            time.sleep(interval_seconds)
    raise ConnectorError("Endpoint data reference was not created in time.")


def pull_data(config: ConnectorConfig, asset_id: str, endpoint_data: dict[str, Any]) -> str:
    endpoint = str(endpoint_data.get("endpoint") or endpoint_data.get("endpointUrl") or "")
    if not endpoint:
        raise ConnectorError(f"Endpoint Data Reference has no endpoint: {endpoint_data}")

    status, body, content_type = request_bytes(
        "GET",
        endpoint,
        headers={"Authorization": str(endpoint_data.get("authorization") or "")},
    )
    if status >= 400:
        raise ConnectorError(f"Pull failed with HTTP {status}: {body.decode('utf-8', errors='replace')}")

    config.downloads_dir.mkdir(parents=True, exist_ok=True)
    path = config.downloads_dir / f"{_safe_filename(asset_id)}{_extension(content_type)}"
    path.write_bytes(body)
    return str(path)


def request_endpoint(
        endpoint_data: dict[str, Any],
        method: str = "GET",
        payload: bytes | str | None = None,
        path: str = "",
        query: dict[str, str] | None = None,
        content_type: str = "application/json",
) -> tuple[int, bytes, str]:
    """Use an Endpoint Data Reference as an authorized HTTP proxy endpoint."""

    endpoint = _append_path_and_query(
        str(endpoint_data.get("endpoint") or endpoint_data.get("endpointUrl") or ""),
        path=path,
        query=query,
    )
    if not endpoint:
        raise ConnectorError(f"Endpoint Data Reference has no endpoint: {endpoint_data}")

    headers = {"Authorization": str(endpoint_data.get("authorization") or "")}
    if payload is not None:
        headers["Content-Type"] = content_type
    return request_bytes(method.upper(), endpoint, payload=payload, headers=headers)


def send_json_via_endpoint(
        endpoint_data: dict[str, Any],
        payload: Any,
        method: str = "POST",
        path: str = "",
        query: dict[str, str] | None = None,
) -> dict[str, Any]:
    encoded = payload if isinstance(payload, str) else json.dumps(payload)
    status, body, content_type = request_endpoint(
        endpoint_data,
        method=method,
        payload=encoded,
        path=path,
        query=query,
        content_type="application/json",
    )
    text = body.decode("utf-8", errors="replace")
    if status >= 400:
        raise ConnectorError(f"EDR {method.upper()} failed with HTTP {status}: {text}")
    return {
        "status": status,
        "contentType": content_type,
        "body": text,
    }


def request_asset(
        config: ConnectorConfig,
        provider_did: str,
        provider_dsp: str,
        offer: Offer
) -> dict[str, str]:
    if not provider_did or not provider_dsp:
        raise ValueError("provider_did and provider_dsp are required before requesting data.")

    negotiation_id = start_negotiation(
        config,
        provider_did=provider_did,
        provider_dsp=provider_dsp,
        asset_id=offer.asset_id,
        offer_id=offer.offer_id,
    )
    agreement_id = wait_for_agreement(config, negotiation_id)

    transfer_id = start_pull_transfer(
        config,
        peer_did=provider_did,
        peer_dsp=provider_dsp,
        agreement_id=agreement_id,
    )
    endpoint_data = wait_for_endpoint_data_reference(config, transfer_id)
    downloaded_file = pull_data(config, offer.asset_id, endpoint_data)

    return {
        "assetId": offer.asset_id,
        "offerId": offer.offer_id,
        "negotiationId": negotiation_id,
        "agreementId": agreement_id,
        "transferId": transfer_id,
        "downloadedFile": downloaded_file,
    }


def negotiate_endpoint_reference(
        config: ConnectorConfig,
        provider_did: str,
        provider_dsp: str,
        offer: Offer,
) -> dict[str, Any]:
    negotiation_id = start_negotiation(
        config,
        provider_did=provider_did,
        provider_dsp=provider_dsp,
        asset_id=offer.asset_id,
        offer_id=offer.offer_id,
    )
    agreement_id = wait_for_agreement(config, negotiation_id)
    transfer_id = start_pull_transfer(
        config,
        peer_did=provider_did,
        peer_dsp=provider_dsp,
        agreement_id=agreement_id,
    )
    endpoint_data = wait_for_endpoint_data_reference(config, transfer_id)
    return {
        "assetId": offer.asset_id,
        "offerId": offer.offer_id,
        "negotiationId": negotiation_id,
        "agreementId": agreement_id,
        "transferId": transfer_id,
        "endpointData": endpoint_data,
    }


def _management_headers(config: ConnectorConfig) -> dict[str, str]:
    return {"x-api-key": config.connector_management_api_key}


def _id_from_response(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    return str(body.get("@id") or body.get("id") or "")


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value or "download"))
    return cleaned.strip("_") or "download"


def _extension(content_type: str) -> str:
    normalized = str(content_type or "").split(";", 1)[0].strip().lower()
    if normalized.endswith("+json"):
        return ".json"
    return {"application/json": ".json", "text/plain": ".txt", "text/html": ".html"}.get(normalized, ".bin")


def _append_path_and_query(base_url: str, path: str = "", query: dict[str, str] | None = None) -> str:
    if not base_url:
        return ""
    url = base_url
    if path:
        url = f"{url.rstrip('/')}/{path.lstrip('/')}"
    if query:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{parse.urlencode(query)}"
    return url
