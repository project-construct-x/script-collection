from __future__ import annotations

from pathlib import Path

import pytest

from config import ConnectorConfig
from publish import build_publish_ids, validate_source_url
from tests.test_util import write_valid_config

def test_explicit_asset_id_produces_stable_related_ids(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"

    write_valid_config(env_file)
    config = ConnectorConfig.from_env(env_file, participant_context_id="participant")

    ids = build_publish_ids(config, "demo-asset")

    assert ids == {
        "assetId": "demo-asset",
        "policyId": "demo-asset-policy",
        "contractDefinitionId": "demo-asset-contract",
    }


def test_relative_publish_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="absolute HTTP"):
        validate_source_url("share/sample.json")


def test_absolute_publish_source_is_preserved() -> None:
    source = "http://backend:8080/api/data"
    assert validate_source_url(source) == source
