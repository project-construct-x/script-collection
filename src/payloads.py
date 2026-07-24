from __future__ import annotations

from typing import Any

EDC_VOCAB = "https://w3id.org/edc/v0.0.1/ns/"
ODRL_CONTEXT = "http://www.w3.org/ns/odrl.jsonld"
ODRL_VOCAB = "http://www.w3.org/ns/odrl/2/"


def asset_payload(
    asset_id: str,
    label: str,
    source_url: str,
    content_type: str = "application/json",
    data_address_type: str = "HttpData",
    proxy_path: bool = False,
    proxy_method: bool = False,
    proxy_body: bool = False,
    proxy_query_params: bool = False,
) -> dict[str, Any]:
    data_address = {
        "type": data_address_type,
        "name": label,
        "baseUrl": source_url,
    }
    if proxy_path:
        data_address["proxyPath"] = "true"
    if proxy_method:
        data_address["proxyMethod"] = "true"
    if proxy_body:
        data_address["proxyBody"] = "true"
    if proxy_query_params:
        data_address["proxyQueryParams"] = "true"

    return {
        "@context": {"@vocab": EDC_VOCAB},
        "@id": asset_id,
        "properties": {"name": label, "contenttype": content_type},
        "dataAddress": data_address,
    }


def empty_policy_definition_payload(policy_id: str) -> dict[str, Any]:
    return {
        "@context": {"@vocab": EDC_VOCAB, "odrl": ODRL_VOCAB},
        "@id": policy_id,
        "policy": {
            "@context": ODRL_CONTEXT,
            "@type": "Set",
            "permission": [],
            "prohibition": [],
            "obligation": [],
        },
    }


def contract_definition_payload(
    contract_definition_id: str,
    policy_id: str,
    asset_id: str,
) -> dict[str, Any]:
    return {
        "@context": {"@vocab": EDC_VOCAB},
        "@id": contract_definition_id,
        "accessPolicyId": policy_id,
        "contractPolicyId": policy_id,
        "assetsSelector": [
            {
                "operandLeft": f"{EDC_VOCAB}id",
                "operator": "=",
                "operandRight": asset_id,
            }
        ],
    }


def catalog_request_payload(peer_dsp: str, protocol: str, peer_did: str = "", limit: int = 0) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "@type": "CatalogRequest",
        "@context": {"@vocab": EDC_VOCAB},
        "counterPartyAddress": peer_dsp,
        "protocol": protocol,
    }
    if peer_did:
        payload["counterPartyId"] = peer_did
    if limit >= 1:
        payload["querySpec"] = {
            "@type": "QuerySpec",
            "limit": limit,
        }
    return payload


def contract_request_payload(
    peer_did: str,
    peer_dsp: str,
    consumer_did: str,
    protocol: str,
    asset_id: str,
    offer_id: str,
) -> dict[str, Any]:
    return {
        "@context": {"@vocab": EDC_VOCAB, "odrl": ODRL_VOCAB},
        "@type": "ContractRequest",
        "counterPartyAddress": peer_dsp,
        "connectorId": peer_did,
        "protocol": protocol,
        "policy": {
            "@context": ODRL_CONTEXT,
            "@id": offer_id,
            "@type": "Offer",
            "assigner": peer_did,
            "assignee": consumer_did,
            "target": asset_id,
        },
    }


def transfer_request_payload(
    peer_did: str,
    peer_dsp: str,
    protocol: str,
    agreement_id: str,
    transfer_type: str = "HttpData-PULL",
    data_destination: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "@context": {"edc": EDC_VOCAB},
        "@type": "TransferRequestDto",
        "protocol": protocol,
        "contractId": agreement_id,
        "counterPartyAddress": peer_dsp,
        "connectorId": peer_did,
        "transferType": transfer_type,
    }
    if data_destination is not None:
        payload["dataDestination"] = data_destination
    return payload


def http_data_destination(
    base_url: str,
    path: str = "",
    method: str = "POST",
    content_type: str = "application/json",
) -> dict[str, str]:
    destination = {
        "type": "HttpData",
        "baseUrl": base_url,
        "method": method,
        "contentType": content_type,
    }
    if path:
        destination["path"] = path
    return destination
