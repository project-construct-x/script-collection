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

from credentials import _is_membership_credential

def test_membership_credential_matches_wallet_metadata() -> None:
    credential = {
        "issuerId": "did:web:issuer.test:issuer",
        "holderId": "did:web:connector.test:participant",
        "state": "ISSUED",
        "metadata": {"credentialObjectId": "dev-credential-def-1"},
        "verifiableCredential": {"rawVc": "encoded-jwt"},
    }

    assert _is_membership_credential(
        credential,
        issuer_did="did:web:issuer.test:issuer",
        credential_definition_id="dev-credential-def-1",
    )


def test_membership_credential_rejects_other_issuer() -> None:
    credential = {
        "issuerId": "did:web:other.test:issuer",
        "metadata": {"credentialObjectId": "dev-credential-def-1"},
    }

    assert not _is_membership_credential(
        credential,
        issuer_did="did:web:issuer.test:issuer",
        credential_definition_id="dev-credential-def-1",
    )
