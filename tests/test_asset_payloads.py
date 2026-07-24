from __future__ import annotations

from payloads import asset_payload


def test_http_read_asset_has_no_proxy_flags() -> None:
    payload = asset_payload(
        asset_id="demo-read-asset",
        label="Demo read asset",
        source_url="http://backend:8080/data",
    )

    data_address = payload["dataAddress"]

    assert data_address["type"] == "HttpData"
    assert "proxyMethod" not in data_address
    assert "proxyBody" not in data_address
    assert "proxyPath" not in data_address
    assert "proxyQueryParams" not in data_address


def test_write_asset_proxies_only_method_and_body() -> None:
    payload = asset_payload(
        asset_id="demo-write-asset",
        label="Demo write asset",
        source_url="http://backend:8080/updates",
        data_address_type="ProxyHttpData",
        proxy_method=True,
        proxy_body=True,
    )

    data_address = payload["dataAddress"]

    assert data_address["type"] == "ProxyHttpData"
    assert data_address["proxyMethod"] == "true"
    assert data_address["proxyBody"] == "true"
    assert "proxyPath" not in data_address
    assert "proxyQueryParams" not in data_address


def test_query_asset_can_proxy_query_params_without_body_or_path() -> None:
    payload = asset_payload(
        asset_id="demo-query-asset",
        label="Query endpoint",
        source_url="http://backend:8080/search",
        content_type="application/json",
        proxy_query_params=True,
    )

    data_address = payload["dataAddress"]

    assert data_address["type"] == "HttpData"
    assert data_address["proxyQueryParams"] == "true"
    assert "proxyMethod" not in data_address
    assert "proxyBody" not in data_address
    assert "proxyPath" not in data_address
