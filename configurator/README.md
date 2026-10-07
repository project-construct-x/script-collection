# Construct-X EDC Python Library

Authors:
Finn Elbl (felbl@uni-wuppertal.de) - TMDT - University of Wuppertal
Alexander Paulus (paulus@uni-wuppertal.de) - TMDT - University of Wuppertal

`cx_edc_client` is a small Python client for operating one Construct-X
EDC connector and executing common data-exchange workflows. It provides an
application-facing API for connector lifecycle operations, participant
onboarding, asset publication, catalog access, contract negotiation, transfers,
and authorized HTTP requests through Endpoint Data References (EDRs).

It packages a local Docker-based deployment of the essential components of an EDC.
The client can also operate an existing, fully configured connector without
accessing its wallet, Vault, or Docker host.

## Features

- Operate a Docker-based connector deployment;
- Operate an existing connector through its Management API;
- Publish HTTP assets, policies, and contract definitions;
- Unpublish assets without deleting their source data;
- Retrieve catalogs and select offers;
- Negotiate contracts;
- Execute pull and `HttpData-PUSH` transfers;

Trusted issuer administration is intentionally excluded. Holder registration,
attestations, and credential definitions remain the responsibility of the
issuer operator.

## Requirements

- Python 3.11 or newer
- Docker with the Compose plugin for local lifecycle operations
- Access to a compatible trusted issuer for local participant onboarding
- Public TCP ports 80 and 443 for standalone HTTPS and ACME certificate issuance
- A valid public domain for a local deployment
- Compatible Control Plane and Data Plane images for the bundled deployment

## Setup

### Installation
Run these commands from `configurator/` to install the library and its CLI:
```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Use `pip install -e ".[dev]"` when developing or running the tests.

### Runtime Images

`edc start` uses the image references in `docker/.docker.env`. The Python
library does not build Docker images. The bundled configuration was tested
with Construct-X Wallet `0.18.0-1`, HashiMock, and the Control Plane and Data
Plane built from `constructx-edc` commit
`021daa740a74c4456a4a02782b88bbce0203247d`.

**Note:** The Control Plane and Data Plane images currently need to be built
locally before starting the connector. The versioned image names in
`docker/.docker.env` refer to local images, not published registry images.

To build the matching planes on a host with Docker and the required JDK:

```bash
git clone https://github.com/project-construct-x/constructx-edc.git
cd constructx-edc
git checkout 021daa740a74c4456a4a02782b88bbce0203247d
./gradlew \
  :edc-controlplane:edc-controlplane-construct-x:con-x-controlplane-postgresql-hashicorp-vault:dockerize \
  :edc-dataplane:edc-dataplane-construct-x:con-x-dataplane-postgresql-hashicorp-vault:dockerize
docker tag con-x-controlplane-postgresql-hashicorp-vault:latest con-x-controlplane-postgresql-hashicorp-vault:0.13.0-021daa74
docker tag con-x-dataplane-postgresql-hashicorp-vault:latest con-x-dataplane-postgresql-hashicorp-vault:0.13.0-021daa74
```

The images must be available on the Docker host running the connector. Access
to the Wallet and HashiMock images may require a GHCR login. Operating an
existing connector through its Management API does not require local images.

### Configuration
Create the runtime environment file from the shipped example
```sh
cp .env.example .env
```

Adjust the contained values _before_ starting the connector.

Important settings include:

| Variable                                | Format                                                              | Comment                                                                          |
|-----------------------------------------|---------------------------------------------------------------------|----------------------------------------------------------------------------------|
| `CONNECTOR_DOMAIN`                      | connector.example.org                                               | Public domain of the participants EDC server                                     |
| `ACME_EMAIL`                            | admin@example.org                                                   | Email to retrieve a LetsEncrypt Certificate                                      |
| `PARTICIPANT_DID`                       | did:web:<connector-domain>:<participant-id>                         | DID of the operator participant                                                  |
| `PARTICIPANT_CONTEXT_ID`                | <participant-id>                                                    | Participant context in the wallet                                                |
| `TRUSTED_ISSUER_DID`                    | did:web:<issuer-host>:<issuer-id>                                   | DID of the membership credential issuer.<br/>Provided by the dataspace operator. |
| `ISSUER_CONTEXT`                        | con-x-issuer                                                        | Prodided by the dataspace operator                                               |
| `TRUSTED_ISSUER_CREDENTIAL_SERVICE_URL` | https://<issuer-host>/api/credentials/v1/participants/<issuer-id>   | Provided by the dataspace operator.                                              |
| `TRUSTED_ISSUER_ISSUANCE_SERVICE_URL`   | https://<issuer-host>/api/issuance/v1beta/participants/<issuer-id> | Provided by the dataspace operator.                                              |

The public paths can be overwritten by uncommenting the respective lines in .env.
If not set explicitly, those values are generated using `CONNECTOR_DOMAIN` as a base URL.

| Variable                             | Format                                                                        | Comment                                                           |
|--------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------|
| `PARTICIPANT_DSP_CALLBACK_ADDRESS`   | https://<connector-domain>/dsp                                                | Public participant DSP base URL, auto-generated if not set        |
| `PARTICIPANT_DATAPLANE_PUBLIC_URL`   | https://<connector-domain>/public                                             | Public participant dataplane URL, auto-generated if not set       |
| `PARTICIPANT_CREDENTIAL_SERVICE_URL` | https://<connector-domain>/api/credentials/v1/participants/<participant-id>   | Public participant credential endpoint, auto-generated if not set |
| `PARTICIPANT_ISSUER_SERVICE_URL`     | https://<connector-domain>/api/issuance/v1beta/participants/<participant-id> | Public participant issuance endpoint, auto-generated if not set   |
| `CONNECTOR_MANAGEMENT_API`           | https://<connector-domain>/management                                         | Control Plane Management API, auto-generated if not set            |

For peer catalog and contract requests, use the versioned DSP endpoint
`https://<peer-domain>/dsp/2025-1`. The configured `/dsp` callback base shown by
`edc status` is not the complete peer endpoint.

The following settings should be changed to random secrets

| Variable                       | Format           | Comment                         |
|--------------------------------|------------------|---------------------------------|
| `PARTICIPANT_SECRET_ALIAS`     | <random>         |                                 |
| `POSTGRES_PASSWORD`            | <random>         | Database password               |
| `WALLET_SUPERUSER_KEY`         | YWRtaW4.<random> | Local wallet administration key |
| `VAULT_TOKEN`                  | <random>         | Local Vault token               |
| `CONNECTOR_MANAGEMENT_API_KEY` | <random>         | Control Plane API Key           |

Relative paths are resolved against the current working directory. Connector
settings are validated when the configuration is loaded. Wallet, Vault, and
trusted issuer settings are validated only when local onboarding is started.

Run `edc config` to create or update the common connector settings
interactively. Local deployment secrets still need to be set directly in
`.env`.

### Operate an Existing Connector

An existing connector must already be deployed, onboarded, and equipped with a
valid participant identity and membership credential. The library only needs
access to its Management API and public DSP endpoint; it does not need direct
access to the connector wallet or Vault.

Configure these values in `.env`:

```text
CONNECTOR_DOMAIN=connector.example.org
CONNECTOR_MANAGEMENT_API=https://connector.example.org/management
CONNECTOR_MANAGEMENT_API_KEY=<management-api-key>
PARTICIPANT_DID=did:web:connector.example.org:user
PARTICIPANT_CONTEXT_ID=user
PARTICIPANT_DSP_CALLBACK_ADDRESS=https://connector.example.org/dsp
```

`CONNECTOR_MANAGEMENT_API` and `PARTICIPANT_DSP_CALLBACK_ADDRESS` are generated
from `CONNECTOR_DOMAIN` when they are not set explicitly.

Verify the connection:

```bash
edc status
```

Afterwards, use `edc publish`, `edc request`, and `edc send-file` as described
below. Do not run `edc start`; that command starts the bundled local deployment
and requires the local wallet, Vault, and trusted issuer configuration.

## Connector Lifecycle

The bundled local deployment is provided through Docker containers. It uses the
Construct-X Vault Mock as a lightweight implementation of the HashiCorp Vault
API for development and demonstrations. Secrets are stored in a persistent
Docker volume and survive normal container and server restarts. Production
deployments should use a properly secured secret-management system.

#### Startup

The startup phase consists of these operations:

1. Start Traefik, PostgreSQL, Vault, the Vault initialization job, and the
   participant wallet;
2. Create or reuse the participant context;
3. Store the participant client secret in Vault;
4. Reuse an existing membership credential or request one from the trusted
   issuer;
5. Wait for the credential;
6. Start the Control Plane and Data Plane.

Participant bootstrap state is stored in `.state/participant.json` unless configured otherwise.
This file contains sensitive credentials and must not be committed or shared.

After installing the Python package, the EDC CLI is available via the `edc` command.
**Run this from the base directory, not within `src`!**

**Note:** Before starting the connector, register your wallet as a holder at
the central issuer. Email your domain-based `did:web` (`PARTICIPANT_DID` in
`.env`) to [david.goerzig@arena2036.de](mailto:david.goerzig@arena2036.de) and
[saud.khan@arena2036.de](mailto:saud.khan@arena2036.de).

Start the connector using:

```bash
edc start
```
This will run all six phases of the startup phase.

#### Data Exchange

Once the connector is running, assets can be published or requested at any time.

Publish an asset:

```bash
edc publish --label "Example Asset" --source share/example.json --content-type json
```

where:

- `--label` specifies the human-readable asset name.
- `--source` specifies either an HTTP endpoint or a file located in the `share/` directory.
- `--content-type` optionally specifies the asset's MIME type. Short forms such as `json`, `txt`, and `png` are also supported.

Place the file in `share/` first and include `share/` in the source path when
running the command from the project directory.

Unpublish an asset:

```bash
edc unpublish --assetid <asset-id>
```

Omit `--assetid` to select an asset from your own catalog. Both modes ask for
confirmation; `-y` skips it.

Unpublishing removes contract definitions that select this asset by its exact
ID, as created by `publish`. The asset, its policies, source data, and existing
contracts remain. Shared contract definitions using other selectors are not
changed; they must be adjusted separately if they also offer the asset.

Request assets from another connector:

```bash
edc request --did <participant-did> --endpoint <dsp-endpoint>
```

If no asset is specified, the available catalog entries are displayed and an asset can be selected interactively.

To directly request a specific asset:

```bash
edc request --did <participant-did> --endpoint <dsp-endpoint> --assetid <asset-id>
```

### Call an HTTP Service with a Text File

`edc send-file` sends the content of a local UTF-8 text file as an authorized
HTTP `POST` request through an Endpoint Data Reference. It performs catalog
discovery, contract negotiation, and EDR retrieval before calling the selected
provider service. The HTTP response is stored in `downloads/`; its file
extension is derived from the response `Content-Type`.

Supported inputs include JSON, CSV, XML, and other UTF-8 text files.
Binary input formats such as DOCX, PDF, ZIP, and images are not supported by
this request path.

The following tested counterpart is available on the external demo connector:

```text
Participant DID: did:web:dataspace-portal.com:dataspace-portal
DSP endpoint:    https://dataspace-portal.com/dsp/2025-1
```

The service implementation is available separately in the
[semantic-mapper repository](https://git.uni-wuppertal.de/tmdt/projects/construct-x/semantic-mapper)
and can also be deployed with its included Docker Compose configuration.

Send a delivery-note JSON file to its semantic mapping service:

```bash
edc send-file \
  --did did:web:dataspace-portal.com:dataspace-portal \
  --endpoint https://dataspace-portal.com/dsp/2025-1 \
  --assetid delivery-note-semantic-mapper \
  --file uploads/delivery-note.json
```

The mapped JSON response is saved as `downloads/delivery-note.json`. Omit
`--file` to select a file from `uploads/` interactively. Omit `--assetid` to
select a compatible service from the provider catalog.

#### Shutdown

Stop the connector stack:

```bash
edc stop
```

> **Warning:** `edc stop --remove` deletes the local connector state (`.state/participant.json`) an all databases, as well as the vault. The connector must be onboarded again before it can participate in data exchange.

## Python Library Usage

All operations are also available separately as part of the ConnectorClient in `src/client.py`.

Refer to the example flows in the `flows` directory for a usage reference.
**Run the flow scripts from the base directory, not within `flows`!**

>Flow scripts can also be executed directly. Modify the default values in each script to the desired endpoints and assets.

### Publish an HTTP Asset

See `flows/publish_asset.py` for an example.

```python
from client import ConnectorClient

client = ConnectorClient()
published = client.publish_http_asset(
    label="Demo asset",
    source_url="https://backend.example.org/data/demo.json",
    asset_id="demo-asset",
)
```

The source URL must be reachable from the provider Data Plane. A fixed asset ID
produces stable policy and contract definition IDs. Existing objects are reused
on HTTP `409`; changed data addresses are not updated automatically.

### Unpublish an Asset

```python
client.unpublish_asset("demo-asset")
```

This uses the configured Management API and does not require wallet or Vault
access. The returned dictionary contains the asset ID and the removed contract
definition IDs. Republishing the same asset ID recreates its offer.

### Request an Asset

See `flows/request_catalog_and_asset.py` for an example.
For all data transfers, _peer_ refers to the remote EDC while _participant_ refers to the active EDC operator.

```python
from client import ConnectorClient

client = ConnectorClient()
catalog = client.fetch_catalog(peer_did="<peer-did>", peer_dsp="<peer-dsp>")
offer = catalog.select_offer(index=0)
result = client.request_http_asset(
   peer_did="<peer-did>",
   peer_dsp="<peer-dsp>",
   offer=offer,
)
```

## Running the local EDC behind an external proxy

By default, this setup runs as a standalone HTTPS service and binds ports 80
and 443. Set `USE_EDGE_PROXY=true` only when a separate edge proxy and the
external Docker network `tmdt-edge-ingress` already exist.

With `USE_EDGE_PROXY=true`, `docker/compose.edge.yml` removes the connector
Traefik's host port bindings and attaches it to `tmdt-edge-ingress` under the
alias `constructx-edc`. The upstream edge proxy must terminate public TLS and
forward HTTP to `http://constructx-edc:443`, preserving the original Host
header. Port 443 is an internal HTTP listener in this mode.

The respective EDC API documentation is available in the [constructx-edc repository](https://github.com/project-construct-x/constructx-edc).
