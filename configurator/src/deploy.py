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

import os
import shutil
import subprocess
import time

from config import ConnectorConfig
from exceptions import ConnectorError
from http_client import request_json
from onboarding import onboard_connector
from vault_seed import prepare_vault_seeds, remove_vault_seeds

INFRASTRUCTURE_SERVICES = ("traefik", "postgres", "edc-wallet", "local-webserver")
CONNECTOR_SERVICES = ("controlplane", "dataplane")

ENV_FILE = ".env"

def _wait_for_wallet(config: ConnectorConfig, attempts: int = 60, interval_seconds: float = 2) -> None:
    url = f"{config.wallet_identity_api}/v1beta/participants/admin"
    headers = {"x-api-key": config.wallet_superuser_key}
    for attempt in range(attempts):
        try:
            status, _ = request_json("GET", url, headers=headers)
            if status == 200:
                return
        except (ConnectorError, ConnectionError):
            pass
        if attempt < attempts - 1:
            time.sleep(interval_seconds)
    raise RuntimeError("Participant wallet did not become ready")


def setup(config: ConnectorConfig | None = None) -> None:
    config = config or ConnectorConfig.from_env(ENV_FILE)
    config.validate_local_onboarding()
    start_infrastructure(config)
    print("Waiting...", "infrastructure startup")
    _wait_for_wallet(config)
    onboarding = onboard_connector(config)
    print("Onboarding", onboarding)

    start_connector(config)


def start_infrastructure(config: ConnectorConfig | None = None) -> None:
    config = config or ConnectorConfig.from_env(ENV_FILE)
    prepare_vault_seeds(config)
    _start_services(config, INFRASTRUCTURE_SERVICES)


def start_connector(config: ConnectorConfig | None = None) -> None:
    config = config or ConnectorConfig.from_env(ENV_FILE)
    _start_services(config, CONNECTOR_SERVICES)


def stop(remove_state: bool = False, config: ConnectorConfig | None = None) -> None:
    config = config or ConnectorConfig.from_env(ENV_FILE)
    _stop_services(config, remove_state=remove_state)
    if remove_state:
        remove_vault_seeds(config)
        config.state_path.unlink(missing_ok=True)


def _start_services(config: ConnectorConfig, services: tuple[str, ...]) -> None:
    if not services:
        raise ValueError("At least one Docker Compose service is required.")
    _run_compose(config, "up", "-d", "--remove-orphans", *services)


def _stop_services(config: ConnectorConfig, remove_state: bool = False) -> None:
    print(f"Stopping services {'and volumes' if remove_state else ''}")
    _run_compose(config, "down", *(["-v"] if remove_state else []), "--remove-orphans")


def _run_compose(config: ConnectorConfig, *args: str) -> None:
    command = [shutil.which("docker") or "docker", "compose", "--project-directory", ".", "-f", "docker/compose.yml"]
    if config.use_edge_proxy:
        command += ["-f", "docker/compose.edge.yml"]
    command += ["--env-file", ENV_FILE, "--env-file", "docker/.docker.env", *args]
    subprocess.run(
        command,
        cwd=config.connector_stack_dir,
        env=dict(os.environ, VAULT_SEED_DIR=str(config.vault_seed_dir)),
        check=True,
    )
