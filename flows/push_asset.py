import json

from catalog import HTTP_PUSH
from client import ConnectorClient
from config import ConnectorConfig

ENV_FILE = ".env"

PARTICIPANT_DID = "enter participant did"
PEER_DID = "enter peer did"
PEER_DSP = "enter peer dsp here"
ASSET_ID = "enter asset id here"
POST_ASSET_ID = "enter post asset id here"

def run_push_asset():
    config = ConnectorConfig.from_env(ENV_FILE)

    client = ConnectorClient(config)

    try:
        client.check_configuration()
    except Exception:
        raise SystemExit("Error during EDC stack check. Setup connector first!") from None

    print("Participant DID:",client.config.participant_did)

    print("\nRequest catalog:")
    catalog = client.fetch_catalog(peer_did=PEER_DID, peer_dsp=PEER_DSP)
    print(catalog)

    print("\nSelect writable asset:")
    offer = catalog.select_offer(asset_id=POST_ASSET_ID)
    assert HTTP_PUSH in offer.formats
    print(offer)

    print("\nNegotiate authorized POST endpoint:")
    endpoint = client.negotiate_endpoint_reference(
        peer_did=PEER_DID,
        peer_dsp=PEER_DSP,
        offer=offer,
    )
    print(
        json.dumps(
            {
                "assetId": endpoint["assetId"],
                "negotiationId": endpoint["negotiationId"],
                "agreementId": endpoint["agreementId"],
                "transferId": endpoint["transferId"],
                "endpoint": endpoint["endpointData"].get("endpoint"),
            },
            indent=2,
        )
    )

    print("\nSend JSON through the dataplane:")

    post_result = client.send_json_via_endpoint(
        endpoint["endpointData"],
        payload={
            "message": "hello from the university connector",
            "source": PARTICIPANT_DID,
            "purpose": "connector POST demonstration",
        },
    )
    print(json.dumps(post_result, indent=2))

if __name__ == "__main__":
    run_push_asset()
