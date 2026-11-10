# Workshop Deployment

This branch runs a local connector with a dedicated Cloudflare Tunnel and a
separate workshop issuer. Ten participant identities are assigned in advance.
It does not use the Construct-X production issuer.

## Participants

Install Python 3.11 or later, Git, and Docker with Linux containers.
Docker Compose 2.24.4 or later is required. The network must allow outbound
Cloudflare Tunnel connections on port 7844 (TCP or UDP).

```powershell
git clone --branch workshop https://github.com/project-construct-x/script-collection.git
cd script-collection/configurator
python -m pip install -e .
Copy-Item .env.example .env
```

Set your assigned hostname and tunnel token in `.env`:

```ini
CONNECTOR_DOMAIN=teilnehmer01.dataspace-portal.com
CLOUDFLARE_TUNNEL_TOKEN=<your individual token>
```

Alternatively, save the individual `.env` provided by the organizer in this directory.
Access to the private GHCR images is required; sign in with an authorized account
or load the images supplied by the organizer before starting.

```powershell
edc start -y
edc status
edc publish --label Materialdaten --source https://example.org/materialdaten.json
edc request --did did:web:teilnehmer02.dataspace-portal.com:participant --endpoint https://teilnehmer02.dataspace-portal.com/dsp/2025-1
edc stop
```

Replace the publish source with a real HTTP(S) resource or a file inside `share/`.
Downloads are saved under `downloads/`. The tunnel exposes DID, credential,
issuance, DSP and data-plane routes, but not management or Vault APIs.
Local secrets are generated on the first `edc start` and retained in `.env`.
Keep `.env` and `.state/` private. Use a separate fresh directory for another seat.

## Organizers

Run `workshop/provision_tunnels.py` with `CLOUDFLARE_API_TOKEN` set privately.
It prepares ten named tunnels and CNAME records and saves individual `.env` files
under `.state/workshop/`. It refuses to replace unrelated DNS entries or tunnels.
The management token must never be distributed to participants.

The issuer deployment is in `docker/workshop-issuer/`. Initialize its attestation,
credential definition and ten holder records before participants request credentials.
Holder registration does not create the local wallet participant or issue a credential;
those steps are performed by `edc start`.
