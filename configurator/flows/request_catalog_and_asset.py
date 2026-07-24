import json
import sys

from client import ConnectorClient
from config import ConnectorConfig
from exceptions import CatalogError
from util import dsp_endpoint_for_protocol

ENV_FILE = ".env"

DEFAULT_ASSET_ID = ""  # leave empty to select on the fly

def run_request_asset(peer_did: str, peer_dsp: str, asset_id: str = "", asset_index: int = -1) -> None:
    config = ConnectorConfig.from_env(ENV_FILE)

    if not peer_did:
        peer_did = config.participant_did
    if not peer_dsp:
        peer_dsp = dsp_endpoint_for_protocol(base_dsp=config.participant_dsp_callback_address, protocol=config.protocol)

    if asset_id:
        print(f"REQUESTING {asset_id} from {peer_did} via {peer_dsp}")
    elif asset_index >= 0:
        print(f"REQUESTING offer {asset_index} from {peer_did} via {peer_dsp}")
    else:
        print(f"REQUESTING selection from {peer_did} via {peer_dsp}")

    config = ConnectorConfig.from_env(ENV_FILE)
    client = ConnectorClient(config)

    try:
        client.check_configuration()
    except Exception:
        raise SystemExit("Error during EDC stack check. Setup connector first!") from None

    print("\nRequesting catalog...")
    catalog = client.fetch_catalog(peer_did=peer_did, peer_dsp=peer_dsp)
    print(catalog)

    print("\nSelect asset:")
    if asset_id:
        try:
            print(f"Auto-selecting asset with id {asset_id}")
            offer = catalog.select_offer(asset_id=asset_id)
        except CatalogError:
            raise SystemExit(f"No matching offer found for asset id: {asset_id}") from None
    elif asset_index >= 0:
        try:
            print(f"Auto-selecting asset at index {asset_index}")
            offer = catalog.select_offer(index=asset_index)
        except CatalogError:
            raise SystemExit(f"No matching offer found for asset index: {asset_index}") from None
    else:
        if len(catalog) == 0:
            raise SystemExit("Peer catalog is empty; nothing to select.")
        try:
            while True:
                raw_choice = input(f"Enter index of offer to select (0-{len(catalog) - 1}): ")
                try:
                    choice = int(raw_choice)
                except ValueError:
                    print("Please enter a valid integer.")
                    continue
                if not (0 <= choice < len(catalog)):
                    print(f"Index out of range: must be between 0 and {len(catalog) - 1}.")
                    continue
                break
        except KeyboardInterrupt:
            print("\nAborted by user.")
            sys.exit(130)  # 130 is the conventional exit code for Ctrl+C

        offer = catalog.select_offer(index=choice)

    print(offer)

    print("\nRequesting asset...")
    result = client.request_http_asset(
        peer_did=peer_did,
        peer_dsp=peer_dsp,
        offer=offer,
    )
    print("\nDownloaded asset:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_request_asset("", "")
    # run_request_asset("did:web:wallet.edc2.construct-x.prod-k8s.eecc.de:edc2", "https://controlplane.edc2.construct-x.prod-k8s.eecc.de/dsp/2025-1", asset_index=0)
