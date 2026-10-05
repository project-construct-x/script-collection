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
