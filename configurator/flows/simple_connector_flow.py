from config import ConnectorConfig
from flows.publish_asset import run_publish
from flows.request_catalog_and_asset import run_request_asset
from flows.start_local import run_start

ENV_FILE = ".env"

if __name__ == "__main__":
    config = ConnectorConfig.from_env(ENV_FILE)

    run_start()
    run_publish("test-json", f"https://{config.connector_domain}/test.json")
    run_request_asset(peer_did=f"{config.participant_did}",
                      peer_dsp=f"{config.participant_dsp_callback_address}",
                      asset_index=0)
