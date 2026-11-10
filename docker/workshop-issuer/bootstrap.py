# Copyright (c) 2026 Bergische Universitaet Wuppertal
# SPDX-License-Identifier: Apache-2.0

"""Initialize only the dedicated workshop issuer and ten preassigned holders."""

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def call(method, url, key, body=None, allowed=(200, 201, 204)):
    req = Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                  headers={"x-api-key": key, "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        if exc.code in allowed:
            return None
        raise RuntimeError(f"{method} {url}: HTTP {exc.code}: {exc.read().decode()}") from exc


def main():
    os.umask(0o077)
    env = dict(line.split("=", 1) for line in Path(".env").read_text().splitlines()
               if line.strip() and not line.startswith("#"))
    context = env["ISSUER_CONTEXT"]
    domain = env["ISSUER_DOMAIN"]
    did = f"did:web:{domain}:{context}"
    public = f"https://{domain}/{context}"
    identity = "http://127.0.0.1:30100/api/identity/v1beta/participants"
    for attempt in range(60):
        try:
            call("GET", identity + "/admin/credentials", env["WALLET_SUPERUSER_KEY"])
            break
        except (RuntimeError, URLError, ConnectionError, TimeoutError):
            if attempt == 59:
                raise
            time.sleep(2)
    state_path = Path(".state/issuer.json")
    if state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = call("POST", identity, env["WALLET_SUPERUSER_KEY"], {
            "roles": [], "active": True, "participantContextId": context, "did": did,
            "serviceEndpoints": [
                {"id": "issuance", "type": "IssuerService",
                 "serviceEndpoint": f"{public}/api/issuance/v1beta/participants/{context}"},
                {"id": "credentials", "type": "CredentialService",
                 "serviceEndpoint": f"{public}/api/credentials/v1/participants/{context}"},
            ],
            "key": {"keyId": did + "#key-1", "privateKeyAlias": did + "-alias",
                    "keyGeneratorParams": {"algorithm": "EdDSA", "curve": "Ed25519"}},
        })
        state_path.parent.mkdir(exist_ok=True, mode=0o700)
        state_path.write_text(json.dumps(state, indent=2))
    admin = f"http://127.0.0.1:30200/api/issuer/v1beta/participants/{context}"
    key = state["apiKey"]
    configuration = {f"did:web:teilnehmer{n:02}.dataspace-portal.com:participant": {
        "workpackages": [4, 5], "memberType": "external", "isMember": True,
    } for n in range(1, 11)}
    configuration.update({"default": {}, "blackList": []})
    call("POST", admin + "/attestations", key, {
        "id": "workshop-members", "attestationType": "dev", "configuration": configuration,
    }, allowed=(200, 201, 204, 409))
    call("POST", admin + "/credentialdefinitions", key, {
        "id": "workshop-membership-v1", "attestations": ["workshop-members"],
        "credentialType": "https://w3id.org/constructx/credentials/v0.1/MembershipCredential",
        "jsonSchema": "{}", "jsonSchemaUrl": "https://dataspace.tmdt.uni-wuppertal.de/workshop-issuer/schema",
        "mappings": [{"input": "content", "output": "credentialSubject", "required": True}],
        "rules": [], "format": "VC1_0_JWT", "validity": 604800,
    }, allowed=(200, 201, 204, 409))
    for did in configuration:
        if not did.startswith("did:"):
            continue
        call("POST", admin + "/holders", key, {"holderId": did, "did": did, "name": did.split(":")[2]},
             allowed=(200, 201, 204, 409))
    print("Workshop issuer initialized: attestation, credential definition and ten holders")


if __name__ == "__main__":
    main()
