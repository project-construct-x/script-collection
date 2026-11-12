# Copyright (c) 2026 Bergische Universität Wuppertal
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at the
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
#
# Contributors:
#   TMDT der Bergischen Universität Wuppertal

from base64 import b64encode
from pathlib import Path
from secrets import token_bytes

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from config import ConnectorConfig
from exceptions import ConnectorError

KEY_FILES = ("wallet_aes", "dataplane_priv", "dataplane_pub")
STS_FILE = "participant_sts"


def prepare_vault_seeds(config: ConnectorConfig) -> None:
    directory = config.vault_seed_dir
    existing = [(directory / name).is_file() for name in KEY_FILES]
    if all(existing):
        return
    if any(existing) or config.state_path.exists():
        raise ConnectorError("SQL Vault keys are missing. Restore the keys or use a fresh stack and participant state.")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = serialization.Encoding.PEM
    private = key.private_bytes(pem, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = key.public_key().public_bytes(pem, serialization.PublicFormat.SubjectPublicKeyInfo)
    for name, content in zip(KEY_FILES, (b64encode(token_bytes(32)), private, public), strict=True):
        _write_seed(directory / name, content)


def write_participant_secret(config: ConnectorConfig, client_secret: str) -> None:
    _write_seed(config.vault_seed_dir / STS_FILE, client_secret.encode("utf-8"))


def remove_vault_seeds(config: ConnectorConfig) -> None:
    for name in (*KEY_FILES, STS_FILE):
        (config.vault_seed_dir / name).unlink(missing_ok=True)


def _write_seed(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.parent.chmod(0o700)
    path.write_bytes(content)
    # Only the individually mounted file must be readable by the container user.
    path.chmod(0o644)
