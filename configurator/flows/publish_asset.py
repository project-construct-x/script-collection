from client import ConnectorClient
from config import ConnectorConfig

ENV_FILE = ".env"

LOCAL_FILE_SERVER_CONTAINER = "local-webserver"
DEFAULT_ASSET_LABEL = "test-asset"
DEFAULT_ASSET_URI = f"http://{LOCAL_FILE_SERVER_CONTAINER}/test.json"
DEFAULT_ASSET_CONTENT_TYPE = "application/json"

def run_publish(asset_label: str, asset_uri: str) -> None:
    config = ConnectorConfig.from_env(ENV_FILE)
    if not asset_label:
        asset_label = DEFAULT_ASSET_LABEL
    if not asset_uri:
        asset_uri = DEFAULT_ASSET_URI

    print(f"Publishing {asset_label} via {asset_uri}")


    client = ConnectorClient(config)

    try:
        client.check_configuration()
    except Exception:
        raise SystemExit("Error during EDC stack check. Setup connector first!") from None

    print("Participant/Publisher DID:")
    print(client.config.participant_did)

    published = client.publish_http_asset(
        label=asset_label,
        source_url=asset_uri,
        content_type="application/json",
    )
    print("Published asset", published)


if __name__ == "__main__":
    run_publish("", "")
