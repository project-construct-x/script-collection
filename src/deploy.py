import shutil
import subprocess
import time
from pathlib import Path

from client import ConnectorClient
from config import ConnectorConfig
from identity import local_credentials, wait_for_membership_credential

INFRASTRUCTURE_SERVICES = ("traefik", "postgres", "edc-vault", "vault-init", "edc-wallet", "local-webserver")
CONNECTOR_SERVICES = ("controlplane", "dataplane")

ENV_FILE = ".env"

config = ConnectorConfig.from_env(ENV_FILE)

def setup() -> None:
    client = ConnectorClient(config)
    start_infrastructure()
    print("Waiting...", "infrastructure startup")
    time.sleep(5)
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
        [docker_path, "compose", "--project-directory", ".", "-f", "docker/compose.yml", "--env-file", ".env",
         "--env-file", "docker/.docker.env", "up", "-d", "--remove-orphans", *services],
        cwd=selected_dir,
        check=True,
    )


def _stop_services(compose_dir: str | Path, remove_state: bool = False) -> None:
    selected_dir = Path(compose_dir)
    print(f"Stopping services {'and volumes' if remove_state else ''}")
    docker_path = shutil.which("docker") or "docker"
    subprocess.run(
        [docker_path, "compose", "--project-directory", ".", "-f", "docker/compose.yml", "--env-file", ".env",
         "--env-file", "docker/.docker.env", "down", *(["-v"] if remove_state else []), "--remove-orphans"],
        cwd=selected_dir,
        check=True,
    )
