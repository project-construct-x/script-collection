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
from urllib.parse import quote, urlparse
from uuid import uuid4

from config import ConnectorConfig
from http_client import ensure_success, request_json
from payloads import EDC_VOCAB, asset_payload, contract_definition_payload, empty_policy_definition_payload
from util import _read

def build_publish_ids(config: ConnectorConfig, asset_id: str | None = None) -> dict[str, str]:
    if asset_id:
        return {
            "assetId": asset_id,
            "policyId": f"{asset_id}-policy",
            "contractDefinitionId": f"{asset_id}-contract",
        }

    suffix = uuid4().hex[:8]
    prefix = config.participant_context_id
    return {
        "assetId": f"{prefix}-asset-{suffix}",
        "policyId": f"{prefix}-policy-{suffix}",
        "contractDefinitionId": f"{prefix}-contract-{suffix}",
    }


def validate_source_url(source_url: str) -> str:
    value = str(source_url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute HTTP(S) URL reachable from the Data Plane.")
    return value


def create_asset(
    config: ConnectorConfig,
    asset_id: str,
    label: str,
    source_url: str,
    content_type: str = "application/json",
    data_address_type: str = "HttpData",
    proxy_path: bool = False,
    proxy_method: bool = False,
    proxy_body: bool = False,
    proxy_query_params: bool = False,
) -> None:
    status, body = request_json(
        "POST",
        f"{config.connector_management_api}/v3/assets",
        asset_payload(
            asset_id,
            label,
            validate_source_url(source_url),
            content_type,
            data_address_type,
            proxy_path=proxy_path,
            proxy_method=proxy_method,
            proxy_body=proxy_body,
            proxy_query_params=proxy_query_params,
        ),
        _management_headers(config),
    )
    ensure_success("create asset", status, body, allowed=(200, 201, 204, 409))


def create_policy_definition(config: ConnectorConfig, policy_id: str) -> None:
    status, body = request_json(
        "POST",
        f"{config.connector_management_api}/v3/policydefinitions",
        empty_policy_definition_payload(policy_id),
        _management_headers(config),
    )
    ensure_success("create policy definition", status, body, allowed=(200, 201, 204, 409))


def create_contract_definition(
    config: ConnectorConfig,
    contract_definition_id: str,
    policy_id: str,
    asset_id: str,
) -> None:
    status, body = request_json(
        "POST",
        f"{config.connector_management_api}/v3/contractdefinitions",
        contract_definition_payload(contract_definition_id, policy_id, asset_id),
        _management_headers(config),
    )
    ensure_success("create contract definition", status, body, allowed=(200, 201, 204, 409))


def publish_asset(
    config: ConnectorConfig,
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
    ids = build_publish_ids(config, asset_id)
    normalized_source = validate_source_url(source_url)

    create_asset(
        config,
        asset_id=ids["assetId"],
        label=label,
        source_url=normalized_source,
        content_type=content_type,
        data_address_type=data_address_type,
        proxy_path=proxy_path,
        proxy_method=proxy_method,
        proxy_body=proxy_body,
        proxy_query_params=proxy_query_params,
    )
    create_policy_definition(config, policy_id=ids["policyId"])
    create_contract_definition(
        config,
        contract_definition_id=ids["contractDefinitionId"],
        policy_id=ids["policyId"],
        asset_id=ids["assetId"],
    )

    return {
        **ids,
        "label": label,
        "sourceUrl": normalized_source,
        "dataAddressType": data_address_type,
        "proxyPath": proxy_path,
        "proxyMethod": proxy_method,
        "proxyBody": proxy_body,
        "proxyQueryParams": proxy_query_params,
    }


def unpublish_asset(config: ConnectorConfig, asset_id: str) -> dict[str, Any]:
    """Remove contract definitions that select this asset by its exact ID."""
    if not asset_id:
        raise ValueError("asset_id is required")

    definition_ids = []
    offset = 0
    while True:
        status, body = request_json(
            "POST",
            f"{config.connector_management_api}/v3/contractdefinitions/request",
            {"@context": {"@vocab": EDC_VOCAB}, "@type": "QuerySpec", "offset": offset, "limit": 100},
            _management_headers(config),
        )
        ensure_success("list contract definitions", status, body, allowed=(200,))
        for definition in body:
            selectors = _read(definition, "assetsSelector", "edc:assetsSelector") or []
            if isinstance(selectors, dict):
                selectors = [selectors]
            if any(
                _read(selector, "operandLeft", "edc:operandLeft") == f"{EDC_VOCAB}id"
                and _read(selector, "operator", "edc:operator") == "="
                and _read(selector, "operandRight", "edc:operandRight") == asset_id
                for selector in selectors
            ):
                definition_ids.append(definition["@id"])
        if len(body) < 100:
            break
        offset += len(body)

    if not definition_ids:
        raise ValueError(f"No contract definition selects asset {asset_id!r} by its exact ID")

    for definition_id in definition_ids:
        status, body = request_json(
            "DELETE",
            f"{config.connector_management_api}/v3/contractdefinitions/{quote(definition_id, safe='')}",
            headers=_management_headers(config),
        )
        ensure_success("delete contract definition", status, body, allowed=(200, 204))
    return {"assetId": asset_id, "contractDefinitionIds": definition_ids}


def _management_headers(config: ConnectorConfig) -> dict[str, str]:
    return {"x-api-key": config.connector_management_api_key}
