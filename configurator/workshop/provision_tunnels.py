# Copyright (c) 2026 Bergische Universitaet Wuppertal
# SPDX-License-Identifier: Apache-2.0

"""Provision ten dedicated workshop tunnels without modifying existing routes."""

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ACCOUNT = "7f7029afa0af5fce5cdd98bcc58ac971"
ZONE = "d959335ccf421fd77f2d345f4cb4a672"
DOMAIN = "dataspace-portal.com"
ROOT = Path(__file__).resolve().parents[1]


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request("https://api.cloudflare.com/client/v4" + path, data=data, method=method,
                  headers={"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"],
                           "Content-Type": "application/json"})
    with urlopen(req, timeout=30) as response:
        result = json.load(response)
    if not result["success"]:
        raise RuntimeError(f"Cloudflare {method} {path} failed")
    return result["result"]


def main():
    destination = ROOT / ".state" / "workshop"
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    tunnels = api("GET", f"/accounts/{ACCOUNT}/cfd_tunnel?is_deleted=false&per_page=100")
    for number in range(1, 11):
        name = f"workshop-teilnehmer{number:02}"
        host = f"teilnehmer{number:02}.{DOMAIN}"
        existing = next((t for t in tunnels if t["name"] == name), None)
        records = api("GET", f"/zones/{ZONE}/dns_records?name={host}")
        if records and (not existing or any(
            r["type"] != "CNAME" or r["content"] != existing["id"] + ".cfargotunnel.com" for r in records
        )):
            raise RuntimeError(f"Refusing to replace existing DNS for {host}")
        if existing:
            # Only reuse our recorded tunnels, never overwrite somebody else's configuration.
            receipt = destination / f"teilnehmer{number:02}.json"
            if not receipt.exists() or json.loads(receipt.read_text())["tunnelId"] != existing["id"]:
                raise RuntimeError(f"Tunnel {name} exists without our local receipt; inspect before reuse")
            tunnel = existing
        else:
            tunnel = api("POST", f"/accounts/{ACCOUNT}/cfd_tunnel", {"name": name, "config_src": "cloudflare"})
            receipt = destination / f"teilnehmer{number:02}.json"
            receipt.write_text(json.dumps({"tunnelId": tunnel["id"], "hostname": host}, indent=2))
        base = f"/accounts/{ACCOUNT}/cfd_tunnel/{tunnel['id']}"
        path = r"^/(participant/did\.json|api/(credentials|issuance)(/.*)?|dsp(/.*)?|public(/.*)?)$"
        api("PUT", base + "/configurations", {"config": {"ingress": [
            {"hostname": host, "path": path, "service": "http://traefik:80"},
            {"service": "http_status:404"},
        ]}})
        if not records:
            api("POST", f"/zones/{ZONE}/dns_records", {"type": "CNAME", "name": host,
                "content": tunnel["id"] + ".cfargotunnel.com", "proxied": True, "ttl": 1})
        token = api("GET", base + "/token")
        env = template.replace("teilnehmer01." + DOMAIN, host).replace(
            "CLOUDFLARE_TUNNEL_TOKEN=change-me", "CLOUDFLARE_TUNNEL_TOKEN=" + token)
        env_path = destination / f"teilnehmer{number:02}.env"
        with env_path.open("w", encoding="utf-8") as output:
            env_path.chmod(0o600)
            output.write(env)
        print(f"Prepared {host}; individual token saved privately")


if __name__ == "__main__":
    main()
