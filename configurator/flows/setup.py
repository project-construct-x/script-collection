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

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(".env")
ENV_EXAMPLE_FILE = Path(".env.example")

@dataclass(frozen=True)
class EnvSetting:
    name: str
    prompt: str
    required: bool = True
    secret: bool = False

SETTINGS = (
    EnvSetting(
        name="CONNECTOR_DOMAIN",
        prompt="Public connector domain",
    ),
    EnvSetting(
        name="ACME_EMAIL",
        prompt="Email address used for ACME certificates",
    ),
    EnvSetting(
        name="PARTICIPANT_DID",
        prompt="Participant DID",
    ),
    EnvSetting(
        name="PARTICIPANT_CONTEXT_ID",
        prompt="Participant context ID",
    ),
    EnvSetting(
        name="PARTICIPANT_SECRET_ALIAS",
        prompt="Participant secret alias",
    ),
    EnvSetting(
        name="TRUSTED_ISSUER_DID",
        prompt="Trusted issuer DID",
    ),
    EnvSetting(
        name="ISSUER_CONTEXT",
        prompt="Trusted issuer context",
    ),
    EnvSetting(
        name="TRUSTED_ISSUER_CREDENTIAL_SERVICE_URL",
        prompt="Trusted issuer credential service URL",
    ),
    EnvSetting(
        name="TRUSTED_ISSUER_ISSUANCE_SERVICE_URL",
        prompt="Trusted issuer issuance service URL",
    ),
    EnvSetting(
        name="MEMBERSHIP_CREDENTIAL_DEFINITION_ID",
        prompt="Membership credential definition ID",
    ),
    EnvSetting(
        name="CONNECTOR_MANAGEMENT_API_KEY",
        prompt="Connector management API key",
        secret=True,
    ),
)

def parse_env_file(path: Path) -> dict[str, str]:
    """Read active KEY=VALUE entries from an env file."""
    values: dict[str, str] = {}

    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()

        if not key:
            continue

        values[key] = strip_optional_quotes(value.strip())

    return values

def strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]

    return value

def format_env_value(value: str) -> str:
    """
    Quote values only when necessary.

    Double quotes, backslashes, newlines and dollar characters are escaped
    when a quoted value is required.
    """
    if not value:
        return ""

    requires_quotes = (
            value != value.strip()
            or any(character.isspace() for character in value)
            or "#" in value
            or '"' in value
            or "'" in value
    )

    if not requires_quotes:
        return value

    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("$", "\\$")
    )

    return f'"{escaped}"'

def masked_value(value: str) -> str:
    if not value:
        return "<not set>"

    if len(value) <= 4:
        return "*" * len(value)

    return f"{value[:2]}{'*' * min(len(value) - 4, 12)}{value[-2:]}"

def prompt_for_value(setting: EnvSetting, current_value: str) -> str:
    while True:
        if setting.secret:
            current_display = masked_value(current_value)
            prompt = (
                f"{setting.prompt} [{current_display}]\n"
                "Enter a new value or press Enter to keep the current value: "
            )
            entered_value = input(prompt)
        else:
            current_display = current_value or "<not set>"
            prompt = f"{setting.prompt} [{current_display}]: "
            entered_value = input(prompt)

        value = entered_value.strip()

        if not value:
            value = current_value

        if setting.required and not value:
            print(f"{setting.name} is required.")
            continue

        return value

def replace_env_values(content: str, values: dict[str, str]) -> str:
    """
    Replace active KEY=VALUE lines while preserving comments and ordering.

    Missing variables are appended to the end of the file.
    Commented variables such as #PARTICIPANT_DSP_CALLBACK_ADDRESS remain
    commented and unchanged.
    """
    lines = content.splitlines()
    updated_keys: set[str] = set()
    updated_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            updated_lines.append(line)
            continue

        key, _ = stripped.split("=", 1)
        key = key.strip()

        if key not in values:
            updated_lines.append(line)
            continue

        updated_lines.append(f"{key}={format_env_value(values[key])}")
        updated_keys.add(key)

    missing_keys = [
        setting.name
        for setting in SETTINGS
        if setting.name in values and setting.name not in updated_keys
    ]

    if missing_keys:
        if updated_lines and updated_lines[-1]:
            updated_lines.append("")

        updated_lines.append("# Values added by the guided setup")

        for key in missing_keys:
            updated_lines.append(f"{key}={format_env_value(values[key])}")

    return "\n".join(updated_lines).rstrip() + "\n"

def write_atomically(path: Path, content: str) -> None:
    directory = path.parent.resolve()

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=directory,
        text=True,
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
            file.write(content)

        temporary_path.replace(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

def ensure_env_file(
        env_file: Path = ENV_FILE,
        example_file: Path = ENV_EXAMPLE_FILE,
) -> bool:
    """
    Ensure that .env exists.

    Returns True when .env was created from .env.example.
    """
    if env_file.exists():
        return False

    if not example_file.exists():
        raise FileNotFoundError(
            f"Cannot initialize connector configuration because "
            f"{example_file} does not exist."
        )

    shutil.copyfile(example_file, env_file)
    return True

def print_current_settings(values: dict[str, str]) -> None:
    print("\nCurrent connector settings:")

    for setting in SETTINGS:
        value = values.get(setting.name, "")

        if setting.secret:
            display_value = masked_value(value)
        else:
            display_value = value or "<not set>"

        print(f"  {setting.name}={display_value}")

def show_configuration(
        env_file: Path = ENV_FILE,
) -> None:
    if not env_file.exists():
        raise FileNotFoundError(
            f"{env_file} does not exist. Run `edc config` first."
        )

    values = parse_env_file(env_file)
    print_current_settings(values)

def run_setup(
        env_file: Path = ENV_FILE,
        example_file: Path = ENV_EXAMPLE_FILE,
) -> None:
    created = ensure_env_file(env_file, example_file)

    if created:
        print(f"Created {env_file} from {example_file}.")
    else:
        print(f"Using existing configuration from {env_file}.")

    current_values = parse_env_file(env_file)

    print(
        "\nEnter the connector settings below. "
        "Press Enter to keep the value shown in brackets.\n"
    )

    updated_values = dict(current_values)

    for setting in SETTINGS:
        updated_values[setting.name] = prompt_for_value(
            setting=setting,
            current_value=current_values.get(setting.name, ""),
        )

    original_content = env_file.read_text(encoding="utf-8")
    updated_content = replace_env_values(original_content, updated_values)

    if updated_content == original_content:
        print(f"\nNo changes made to {env_file}.")
        return

    write_atomically(env_file, updated_content)
    print(f"\nConnector configuration written to {env_file}.")
