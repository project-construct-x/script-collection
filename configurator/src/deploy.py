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

import shutil
import subprocess
import time
from pathlib import Path

from client import ConnectorClient
from config import ConnectorConfig
from exceptions import ConnectorError
from http_client import request_json
from identity import local_credentials, wait_for_membership_credential

INFRASTRUCTURE_SERVICES = ("traefik", "postgres", "edc-vault", "vault-init", "edc-wallet", "local-webserver")
CONNECTOR_SERVICES = ("controlplane", "dataplane")

ENV_FILE = ".env"

config = ConnectorConfig.from_env(ENV_FILE)


def _compose_file_args() -> list[str]:
    files = ["docker/compose.yml"]
    if config.use_edge_proxy:
        files.append("docker/compose.edge.yml")
    return [argument for path in files for argument in ("-f", path)]


def _wait_for_wallet(attempts: int = 60, interval_seconds: float = 2) -> None:
    url = f"{config.wallet_identity_api}/v1beta/participants"
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


def setup() -> None:
    client = ConnectorClient(config)
    start_infrastructure()
    print("Waiting...", "infrastructure startup")
    _wait_for_wallet()
    onboarding = client.bootstrap_participant()
    print("Onboarding", onboarding)

    credentials = local_credentials(config)
    if not credentials:
        print("Obtaining membership credentials...")
        client.request_membership_credential()
        credentials = wait_for_membership_credential(config)

    print(
        "Wallet credentials",
        [
            {
                "issuerId": credential.get("issuerId"),
                "holderId": credential.get("holderId"),
                "credentialObjectId": (credential.get("metadata") or {}).get("credentialObjectId"),
                "rawVcPresent": bool((credential.get("verifiableCredential") or {}).get("rawVc")),
            }
            for credential in credentials
        ],
    )

    start_connector()


def start_infrastructure() -> None:
    _start_services(config.connector_stack_dir, INFRASTRUCTURE_SERVICES)


def start_connector() -> None:
    _start_services(config.connector_stack_dir, CONNECTOR_SERVICES)


def stop(remove_state: bool = False) -> None:
    _stop_services(config.connector_stack_dir, remove_state=remove_state)


def _start_services(compose_dir: str | Path, services: tuple[str, ...]) -> None:
    if not services:
        raise ValueError("At least one Docker Compose service is required.")
    selected_dir = Path(compose_dir)

    docker_path = shutil.which("docker") or "docker"
    subprocess.run(
        [docker_path, "compose", "--project-directory", ".", *_compose_file_args(), "--env-file", ".env",
         "--env-file", "docker/.docker.env", "up", "-d", "--remove-orphans", *services],
        cwd=selected_dir,
        check=True,
    )


def _stop_services(compose_dir: str | Path, remove_state: bool = False) -> None:
    selected_dir = Path(compose_dir)
    print(f"Stopping services {'and volumes' if remove_state else ''}")
    docker_path = shutil.which("docker") or "docker"
    subprocess.run(
        [docker_path, "compose", "--project-directory", ".", *_compose_file_args(), "--env-file", ".env",
         "--env-file", "docker/.docker.env", "down", *(["-v"] if remove_state else []), "--remove-orphans"],
        cwd=selected_dir,
        check=True,
    )
