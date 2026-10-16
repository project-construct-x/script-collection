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
from deploy import setup
from flows.publish_asset import run_publish
from flows.request_catalog_and_asset import run_request_asset

ENV_FILE = ".env"

if __name__ == "__main__":
    config = ConnectorConfig.from_env(ENV_FILE)

    setup()
    run_publish("test-json", f"https://{config.connector_domain}/test.json")
    run_request_asset(peer_did=f"{config.participant_did}",
                      peer_dsp=config.dsp_endpoint,
                      asset_index=0)
