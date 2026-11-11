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

import argparse
import json
from pathlib import Path
from typing import Any

from client import ConnectorClient


def call_http_service(peer_did: str, peer_dsp: str, asset_id: str, payload: Any) -> dict[str, Any]:
    """Send JSON to a provider service through an authorized data plane endpoint."""
    client = ConnectorClient()
    catalog = client.fetch_catalog(peer_did=peer_did, peer_dsp=peer_dsp)
    offer = catalog.select_offer(asset_id=asset_id)
    endpoint = client.negotiate_endpoint_reference(
        peer_did=peer_did,
        peer_dsp=peer_dsp,
        offer=offer,
    )
    return client.send_json_via_endpoint(endpoint["endpointData"], payload=payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a JSON file to an EDC service asset.")
    parser.add_argument("--did", required=True, help="Provider DID")
    parser.add_argument("--endpoint", required=True, help="Provider DSP endpoint")
    parser.add_argument("--assetid", required=True, help="Service asset ID")
    parser.add_argument("--file", required=True, type=Path, help="JSON input file")
    args = parser.parse_args()
    try:
        payload = args.file.read_text(encoding="utf-8")
        json.loads(payload)
    except (OSError, ValueError) as exc:
        parser.error(f"Could not read JSON input: {exc}")
    result = call_http_service(args.did, args.endpoint, args.assetid, payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
